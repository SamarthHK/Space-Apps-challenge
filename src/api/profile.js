export const profileFields = [
  ['name', 'Shared profile name'],
  ['kannada_name', 'Name in Kannada'],
  ['phone', 'Contact phone', null, 32],
  ['soil_health_card_no', 'Soil Health Card reference (not verified)', null, 100],
  ['state', 'State'], ['district', 'District'], ['taluk', 'Taluk'], ['village', 'Village'],
  ['farmer_category', 'Farmer category', [
    ['small_marginal', 'Small or marginal'], ['medium', 'Medium'], ['large', 'Large'],
  ]],
  ['preferred_language', 'Preferred language', [['en', 'English'], ['kn', 'Kannada']]],
  ['risk_tolerance', 'Risk tolerance', [
    ['conservative', 'Conservative'], ['balanced', 'Balanced'], ['progressive', 'Progressive'],
  ]],
  ['primary_objective', 'Primary objective', [
    ['profit_maximization', 'Profit maximization'], ['low_water_risk', 'Water conservation'],
    ['household_security', 'Household food security'],
  ]],
];

export function profileChanges(form, original) {
  return Object.fromEntries(profileFields.flatMap(([key]) => {
    const input = form.get(key);
    if (typeof input !== 'string') throw new Error(`Missing profile control: ${key}`);
    const value = input.trim() === '' ? null : input;
    return value === original[key] ? [] : [[key, value]];
  }));
}
