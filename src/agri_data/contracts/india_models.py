"""Comparable conditional reference scorers; no planted-crop or raw-yield classification."""

import gc
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .model_resources import ResourceMonitor, admit
from .outcome_data import write_json
from .storage_proof import require


def feature_definition(train, schema, groups=None):
    allowed = set(groups) if groups is not None else {item["group"] for item in schema.values()}
    names, dropped = [], {}
    for name, definition in sorted(schema.items()):
        if definition["group"] not in allowed:
            dropped[name] = "excluded_feature_group"
        elif train[name].isna().all():
            dropped[name] = "all_missing_in_training"
        elif train[name].nunique(dropna=False) == 1:
            dropped[name] = "constant_in_training"
        elif any(train[name].equals(train[previous]) for previous in names):
            dropped[name] = "exact_duplicate_in_training"
        else:
            names.append(name)
    require(names, "Training has no varying features")
    return {"features": names, "categorical": [name for name in names if schema[name]["dtype"] == "categorical"],
            "numeric": [name for name in names if schema[name]["dtype"] == "numeric"], "dropped": dropped,
            "crop_system_support": [list(pair) for pair in sorted(set(zip(train.crop_id, train.production_system)))]}


def model_inputs(frame, state):
    values = frame[state["features"]].copy()
    for name in state["categorical"]:
        values[name] = values[name].fillna("__missing__").astype(str)
    for name in state["numeric"]:
        values[name] = values[name].astype(float)
        require(not np.isinf(values[name].to_numpy()).any(), "Non-finite model input")
    return values


def check_support(frame, state):
    require(set(zip(frame.crop_id, frame.production_system)) <=
            {tuple(pair) for pair in state["crop_system_support"]}, "Unsupported trained crop/system combination")


def _neural_arrays(frame, state):
    values = model_inputs(frame, state)
    raw = values[state["numeric"]].to_numpy(dtype=np.float32)
    mask = np.isfinite(raw)
    means = np.array(state["means"], dtype=np.float32)
    scales = np.array(state["scales"], dtype=np.float32)
    numeric = np.where(mask, (raw - means) / scales, 0).astype(np.float32)
    numeric = np.concatenate((numeric, mask.astype(np.float32)), axis=1)
    encoded = [values[name].map(state["categories"][name]).fillna(0).to_numpy(dtype=np.int64)
               for name in state["categorical"]]
    categories = np.column_stack(encoded) if encoded else np.empty((len(frame), 0), dtype=np.int64)
    return numeric, categories


def _network(state):
    import torch
    from torch import nn

    class Scorer(nn.Module):
        def __init__(self):
            super().__init__()
            sizes = [len(state["categories"][name]) + 1 for name in state["categorical"]]
            dimensions = [min(16, max(2, math.ceil(math.sqrt(size)))) for size in sizes]
            self.embeddings = nn.ModuleList(nn.Embedding(size, dimension) for size, dimension in zip(sizes, dimensions))
            width = len(state["numeric"]) * 2 + sum(dimensions)
            hidden = state["parameters"]["hidden"]
            self.layers = nn.Sequential(nn.Linear(width, hidden), nn.ReLU(),
                                        nn.Dropout(state["parameters"]["dropout"]),
                                        nn.Linear(hidden, hidden // 2), nn.ReLU(),
                                        nn.Linear(hidden // 2, 1), nn.Sigmoid())

        def forward(self, numeric, categories):
            embedded = [module(categories[:, index]) for index, module in enumerate(self.embeddings)]
            return self.layers(torch.cat([numeric, *embedded], dim=1)).squeeze(1)

    return Scorer()


def _neural_predict(model, frame, state):
    import torch
    numeric, categories = _neural_arrays(frame, state)
    output = []
    model.eval()
    with torch.no_grad():
        for start in range(0, len(frame), state["parameters"]["batch_size"]):
            end = start + state["parameters"]["batch_size"]
            output.append(model(torch.from_numpy(numeric[start:end]), torch.from_numpy(categories[start:end])).numpy())
    return np.concatenate(output).astype(float) if output else np.empty(0)


def fit_estimator(train, validation, schema, method, parameters, monitor, groups=None):
    state = feature_definition(train, schema, groups)
    state.update(method=method, parameters=parameters)
    require(np.isfinite(train.target).all() and train.target.between(0, 1).all(), "Invalid reference training labels")
    if validation is not None:
        check_support(validation, state)
    if method == "baseline":
        state["medians"] = {crop + "|" + system: float(value) for (crop, system), value in
                            train.groupby(["crop_id", "production_system"]).target.median().items()}
        state["selected_iterations"] = 0
        model = None
    elif method == "catboost":
        from catboost import CatBoostRegressor
        model = CatBoostRegressor(iterations=parameters["iterations"], depth=parameters["depth"],
                                  learning_rate=parameters["learning_rate"], l2_leaf_reg=parameters["l2_leaf_reg"],
                                  random_seed=parameters["seed"], loss_function="RMSE", eval_metric="MAE",
                                  thread_count=2, verbose=False, allow_writing_files=False)
        fit_args = {}
        if validation is not None:
            fit_args.update(eval_set=(model_inputs(validation, state), validation.target),
                            early_stopping_rounds=parameters.get("patience", 50), use_best_model=True)
        model.fit(model_inputs(train, state), train.target, cat_features=state["categorical"],
                  callbacks=[monitor], **fit_args)
        state["selected_iterations"] = int(model.tree_count_)
        state["feature_importance"] = dict(zip(state["features"], map(float, model.feature_importances_)))
    elif method == "mlp":
        import torch
        torch.set_num_threads(2)
        torch.manual_seed(parameters["seed"])
        raw = model_inputs(train, state)
        state["means"] = [float(raw[name].mean()) for name in state["numeric"]]
        state["scales"] = [max(float(raw[name].std(ddof=0)), 1e-6) for name in state["numeric"]]
        state["categories"] = {name: {value: index + 1 for index, value in
                                      enumerate(sorted(raw[name].unique()))} for name in state["categorical"]}
        numeric, categories = _neural_arrays(train, state)
        numeric, categories = torch.from_numpy(numeric), torch.from_numpy(categories)
        target = torch.from_numpy(train.target.to_numpy(dtype=np.float32))
        model = _network(state)
        optimizer = torch.optim.AdamW(model.parameters(), lr=parameters["learning_rate"],
                                      weight_decay=parameters["weight_decay"])
        random = np.random.default_rng(parameters["seed"])
        best, best_epoch, best_weights = math.inf, 0, None
        for epoch in range(parameters["epochs"]):
            monitor.check()
            model.train()
            order = random.permutation(len(train))
            for start in range(0, len(order), parameters["batch_size"]):
                chosen = order[start:start + parameters["batch_size"]]
                optimizer.zero_grad(set_to_none=True)
                prediction = model(numeric[chosen], categories[chosen])
                loss = torch.nn.functional.mse_loss(prediction, target[chosen])
                require(torch.isfinite(loss).item(), "Neural loss became non-finite")
                loss.backward()
                optimizer.step()
            value = float(np.mean(np.abs(_neural_predict(model, validation, state) - validation.target.to_numpy()))) \
                if validation is not None else 0
            if validation is None or value < best:
                best, best_epoch = value, epoch + 1
                best_weights = {key: value.detach().clone() for key, value in model.state_dict().items()}
            elif epoch + 1 - best_epoch >= parameters["patience"]:
                break
        require(best_weights is not None, "Neural training did not produce a checkpoint")
        model.load_state_dict(best_weights)
        model.eval()
        state["selected_iterations"] = best_epoch
        state["missing_representation"] = "scaled_numeric_padding_zero_plus_observation_mask_not_stored_imputation"
    else:
        raise ValueError("Unsupported reference model architecture")
    monitor.check()
    return model, state


def fit_admitted(train, validation, schema, method, parameters, groups=None):
    if method == "mlp":
        import torch
        torch.set_num_threads(2)
    elif method == "catboost":
        import catboost  # noqa: F401
    admit(64 * 1024 ** 2)
    probe_parameters = dict(parameters)
    probe_parameters["iterations"] = min(parameters.get("iterations", 1), 12)
    probe_parameters["epochs"] = min(parameters.get("epochs", 1), 2)
    probe = train.iloc[:min(8192, len(train))]
    with ResourceMonitor() as profile:
        trial, _ = fit_estimator(probe, None, schema, method, probe_parameters, profile, groups)
    profile_report = profile.report()
    del trial
    gc.collect()
    input_bytes = int(train.memory_usage(deep=True).sum())
    ratio = max(1, len(train) / len(probe)) if method == "catboost" else 1
    tree_bytes = parameters.get("iterations", 0) * 2 ** parameters.get("depth", 0) * 64
    estimate = max(int(profile_report["incremental_peak_bytes"] * ratio) + tree_bytes, input_bytes * 3,
                   32 * 1024 ** 2)
    admission = admit(estimate)
    with ResourceMonitor() as monitor:
        model, state = fit_estimator(train, validation, schema, method, parameters, monitor, groups)
    telemetry = {"profile": profile_report, "admission": admission, "training": monitor.report()}
    require(not telemetry["training"]["reserve_breached"], "Training breached the resource reserve")
    state["resource_telemetry"] = telemetry
    return model, state


def predict_estimator(model, state, frame):
    check_support(frame, state)
    if state["method"] == "baseline":
        prediction = np.array([state["medians"][crop + "|" + system]
                               for crop, system in zip(frame.crop_id, frame.production_system)])
    elif state["method"] == "catboost":
        prediction = model.predict(model_inputs(frame, state), thread_count=2)
    else:
        prediction = _neural_predict(model, frame, state)
    require(np.isfinite(prediction).all(), "Non-finite reference model score")
    return np.clip(np.asarray(prediction, dtype=float), 0, 1)


def save_estimator(model, state, path, prefix):
    path = Path(path)
    write_json(path / (prefix + ".state.json"), state)
    if state["method"] == "catboost":
        model.save_model(str(path / (prefix + ".cbm")))
    elif state["method"] == "mlp":
        import torch
        torch.save(model.state_dict(), path / (prefix + ".pt"))


def load_estimator(path, prefix):
    path = Path(path)
    state = json.loads((path / (prefix + ".state.json")).read_bytes())
    model = None
    if state["method"] == "catboost":
        from catboost import CatBoostRegressor
        model = CatBoostRegressor()
        model.load_model(str(path / (prefix + ".cbm")))
    elif state["method"] == "mlp":
        import torch
        torch.set_num_threads(2)
        model = _network(state)
        model.load_state_dict(torch.load(path / (prefix + ".pt"), map_location="cpu", weights_only=True))
        model.eval()
    return model, state


def _tie_aware_dcg(relevance, scores, k):
    order = np.argsort(-scores, kind="stable")
    discounts = 1 / np.log2(np.arange(2, min(k, len(order)) + 2))
    result, start = 0.0, 0
    while start < len(discounts):
        end = start + 1
        while end < len(order) and scores[order[end]] == scores[order[start]]:
            end += 1
        result += float(relevance[order[start:end]].mean()) * float(discounts[start:min(end, len(discounts))].sum())
        start = end
    return result


def reference_metrics(frame, predictions):
    prediction = np.asarray(predictions, dtype=float)
    target = frame.target.to_numpy()
    require(len(prediction) == len(frame) and np.isfinite(prediction).all(), "Invalid evaluation predictions")

    def errors(indices):
        difference = (prediction[indices] - target[indices]) * 100
        return {"rows": len(indices), "mae_index_points": float(np.abs(difference).mean()),
                "rmse_index_points": float(np.sqrt(np.square(difference).mean()))}

    groups = {name: {str(key): errors(indices) for key, indices in frame.groupby(name).indices.items()}
              for name in ("crop_id", "production_system", "period_id", "spatial_group")}
    ndcg, top1, regret, uninformative = [], [], [], 0
    for indices in frame.groupby(["context_id", "production_system"]).indices.values():
        truth, score = target[indices], prediction[indices]
        ideal = _tie_aware_dcg(truth, truth, 5)
        if len(indices) < 2 or ideal <= 0:
            uninformative += 1
            continue
        ndcg.append(_tie_aware_dcg(truth, score, 5) / ideal)
        tied = score == score.max()
        top1.append(float((truth[tied] >= truth.max() - 1e-12).mean()))
        regret.append(float((truth.max() - truth[tied].mean()) * 100))
    return {**errors(np.arange(len(frame))),
            "macro_crop_mae_index_points": float(np.mean([row["mae_index_points"] for row in groups["crop_id"].values()])),
            "ndcg_at_5": float(np.mean(ndcg)) if ndcg else None,
            "top1_reference_agreement": float(np.mean(top1)) if top1 else None,
            "top1_reference_regret_points": float(np.mean(regret)) if regret else None,
            "ranked_contexts": len(ndcg), "uninformative_ranking_contexts": uninformative,
            "ranking_scope": "comparable_GAEZ_indices_not_next_season_or_farm_success",
            "by": groups}
