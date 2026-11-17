// Pure JXA control-flow tests; actual Accessibility behavior needs macOS checks.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('scripts/finder_actions.js', 'utf8');
function scenario(action, role, {front = true, selected = true, pending = '', copied = true} = {}) {
    const events = [];
    let marker = pending;
    let changes = 1;
    const pb = {
        get changeCount() { return changes; },
        stringForType() { return marker; },
        setStringForType(value) { marker = value; changes++; },
    };
    const $ = x => x;
    $.NSPasteboard = {generalPasteboard: pb};
    const attr = value => ({value: () => value});
    const root = {attributes: {byName: () => attr('AXWindow')}};
    const element = {attributes: {byName: name => attr(name === 'AXRole' ? role : root)}};
    const se = {processes: {byName: () => ({attributes: {byName: () => attr(element)}})},
        keyCode(code, options) {
            events.push([code, options.using]);
            if (code === 8 && copied) { marker = ''; changes++; }
        }};
    const finder = {frontmost: () => front, selection: () => selected ? ['file'] : []};
    const context = vm.createContext({$, ObjC: {import() {}, unwrap: x => x},
        Application: name => name === 'Finder' ? finder : se, delay() {}});
    vm.runInContext(source, context);
    context.run([action]);
    return {events: JSON.parse(JSON.stringify(events)), marker};
}
assert.deepEqual(scenario('trash', 'AXTextField').events, [[117, []]]);
assert.deepEqual(scenario('delete', 'AXTextArea').events, [[117, ['shift down']]]);
assert.deepEqual(scenario('trash', 'AXOutline').events, [[51, ['command down']]]);
assert.deepEqual(scenario('delete', 'AXOutline').events, [[51, ['command down', 'option down']]]);
assert.deepEqual(scenario('trash', 'AXButton').events, []);
assert.deepEqual(scenario('trash', 'AXOutline', {front: false}).events, []);
assert.deepEqual(scenario('trash', 'AXOutline', {selected: false}).events, []);
assert.equal(scenario('cut', 'AXOutline').marker, 'move');
assert.equal(scenario('cut', 'AXOutline', {copied: false}).marker, '');
assert.deepEqual(scenario('paste', 'AXOutline', {pending: 'move'}).events, [[9, ['command down', 'option down']]]);
assert.deepEqual(scenario('paste', 'AXOutline').events, [[9, ['command down']]]);
assert.equal(scenario('cancel', 'AXOutline', {pending: 'move'}).marker, '');
assert.deepEqual(scenario('paste', 'AXTextField', {pending: 'move'}).events, [[9, ['command down']]]);
console.log('Finder helper: 13 control-flow checks passed');
