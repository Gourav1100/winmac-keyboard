/* Invoked by Karabiner using osascript -l JavaScript. No filesystem deletion. */
ObjC.import('AppKit');
function run(argv) {
    const action = argv[0];
    const se = Application('System Events');
    const finder = Application('Finder');
    const pb = $.NSPasteboard.generalPasteboard;
    const marker = $('org.winmac-keyboard.pending-move');
    function frontmost() { return finder.frontmost(); }
    function press(code, mods) {
        if (!frontmost()) return;
        se.keyCode(code, {using: mods || []});
    }
    if (!frontmost()) return;
    // Fail closed when Accessibility cannot establish the focused element.
    let element = se.processes.byName('Finder').attributes.byName('AXFocusedUIElement').value();
    let editing = false;
    let fileView = false;
    for (let depth = 0; element && depth < 12; depth++) {
        const role = element.attributes.byName('AXRole').value();
        if (['AXTextField', 'AXTextArea', 'AXComboBox'].indexOf(role) >= 0) {
            editing = true;
            break;
        }
        if (['AXOutline', 'AXBrowser', 'AXList', 'AXTable', 'AXScrollArea'].indexOf(role) >= 0) fileView = true;
        if (role === 'AXWindow' || role === 'AXApplication') break;
        element = element.attributes.byName('AXParent').value();
    }
    function clearMove() {
        if (pb.stringForType(marker)) pb.setStringForType($(''), marker);
    }
    if (editing) {
        clearMove();
        if (action === 'trash' || action === 'delete') press(117, action === 'delete' ? ['shift down'] : []);
        else if (action === 'cut') press(7, ['command down']);
        else if (action === 'paste') press(9, ['command down']);
        else if (action === 'cancel') press(53);
        else if (action === 'rename') press(36);
        return;
    }
    if (!fileView) return; // Do not act on an unidentified focused control.
    if (action === 'cancel') { clearMove(); press(53); return; }
    if (action === 'paste') {
        const pending = pb.stringForType(marker);
        const move = pending && ObjC.unwrap(pending) === 'move';
        clearMove();
        press(9, move ? ['command down', 'option down'] : ['command down']);
        return;
    }
    if (finder.selection().length === 0) return;
    clearMove();
    if (action === 'cut') {
        const before = Number(pb.changeCount);
        press(8, ['command down']);
        for (let n = 0; n < 30 && Number(pb.changeCount) === before; n++) delay(0.02);
        if (frontmost() && Number(pb.changeCount) !== before) {
            // Extend Finder's clipboard types without discarding its file URLs.
            pb.addTypesOwner([marker], null);
            if (!pb.setStringForType($('move'), marker)) {
                throw new Error('WinMac: could not mark Finder clipboard for a pending move');
            }
        }
    } else if (action === 'trash') press(51, ['command down']);
    else if (action === 'delete') press(51, ['command down', 'option down']);
    else if (action === 'rename') press(36);
}
