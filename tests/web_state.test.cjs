// Optional browser-state regressions: node --test tests/web_state.test.cjs
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function editor() {
  const listeners = new Map();
  const button = { disabled: true };
  const status = { textContent: '' };
  const badge = { textContent: '' };
  const form = {
    id: 'project-form', dataset: { ipv6Usage: 'no' },
    elements: {
      revision: { value: '1' },
      ipv6_usage: { value: 'no', dataset: { bound: 'true' } },
      new_kind: { value: 'site', dataset: { parentChoicesBound: 'true' } },
      new_parent: { options: [], selectedOptions: [] },
      new_name: { value: 'Nowa lokalizacja' },
      planning_mode: { value: 'review' },
    },
    closest: () => form,
    querySelectorAll: () => [],
  };
  const nodes = {
    '#project-form': form, '#save-status': badge, '#preview-status': status,
    '#apply-preview button[type="submit"]': button,
    'meta[name="csrf-token"]': { content: 'test-token' },
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,
    '../src/adresplan/web/static/app.js'), 'utf8'), {
    document: {
      addEventListener: (name, fn) => listeners.set(name, [...(listeners.get(name) || []), fn]),
      querySelector: (selector) => nodes[selector] || null,
    },
    window: { addEventListener: () => {} },
    Set, Map,
  });
  const emit = (name, event) => {
    for (const listener of listeners.get(name) || []) listener(event);
  };
  const request = () => {
    const xhr = { status: 200, getResponseHeader: (name) => name === 'X-Plan-Preview' ? '1' : null };
    emit('htmx:beforeRequest', { detail: { elt: form, xhr, requestConfig: { parameters: {} } } });
    return xhr;
  };
  const finish = (xhr) => emit('htmx:afterRequest', { detail: { xhr } });
  const edit = () => emit('input', { target: form });
  const submit = () => {
    let prevented = false;
    emit('submit', { target: { id: 'apply-preview' }, preventDefault: () => { prevented = true; } });
    return prevented;
  };
  return { emit, request, finish, edit, submit, form, button };
}

test('latest edit must be recalculated before preview can be committed', () => {
  const page = editor();
  page.edit();
  page.finish(page.request());
  assert.equal(page.button.disabled, false);
  page.edit();
  assert.equal(page.button.disabled, true);
  assert.equal(page.submit(), true);
  page.finish(page.request());
  assert.equal(page.button.disabled, false);
  assert.equal(page.submit(), false);
});

test('response to an older edit cannot enable committing a newer edit', () => {
  const page = editor();
  page.edit();
  const older = page.request();
  page.edit();
  page.finish(older);
  assert.equal(page.button.disabled, true);
  assert.equal(page.submit(), true);
  page.finish(page.request());
  assert.equal(page.button.disabled, false);
});

test('failed preview and structural request keep commit blocked', () => {
  const page = editor();
  page.edit();
  page.finish(page.request());
  page.emit('submit', { target: page.form });
  assert.equal(page.button.disabled, true);
  const xhr = page.request();
  xhr.status = 422;
  page.finish(xhr);
  assert.equal(page.button.disabled, true);
  assert.equal(page.submit(), true);
});

test('IPv6 change preserves the explicitly selected add or freeze action', () => {
  const page = editor();
  page.form.elements.ipv6_usage.value = 'yes';
  for (const action of ['add', 'freeze', 'template-apply', 'save', undefined]) {
    const detail = { elt: page.form, headers: {}, parameters: { action } };
    page.emit('htmx:configRequest', { detail });
    assert.equal(detail.parameters.action, !action || action === 'save' ? 'ipv6-toggle' : action);
  }
});
