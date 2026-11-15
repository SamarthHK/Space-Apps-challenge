import { test } from 'node:test';
import assert from 'node:assert/strict';
import { profileFields, profileChanges } from '../src/api/profile.js';

test('profile patches contain only changed writable fields and explicit clearing', () => {
  const original = Object.fromEntries(profileFields.map(([key]) => [key, null]));
  original.name = 'Shared workspace';
  const form = new FormData();
  profileFields.forEach(([key]) => form.set(key, original[key] ?? ''));
  assert.deepEqual(profileChanges(form, original), {});
  form.set('name', '  ');
  form.set('preferred_language', 'kn');
  form.set('version', 'unexpected-body-version');
  assert.deepEqual(profileChanges(form, original), { name: null, preferred_language: 'kn' });
});
