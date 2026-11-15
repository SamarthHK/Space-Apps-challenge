import Ajv from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import contract from '../../contracts/openapi.json' with { type: 'json' };

const validator = new Ajv({ strict: false });
addFormats(validator);
validator.addSchema({ $id: 'contract', components: contract.components }, 'contract');
const schemas = new Map();

export function validateResponse(name, value) {
  if (!schemas.has(name)) {
    schemas.set(name, validator.compile({ $ref: `contract#/components/schemas/${name}` }));
  }
  return schemas.get(name)(value);
}
