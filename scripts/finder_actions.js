/* Invoked by Karabiner using osascript -l JavaScript. No filesystem deletion. */
ObjC.import('AppKit');
function run(argv) {
    let stage = 'initialization';
    try {
        const action = argv[0];
        const se = Application('System Events');
        const finder = Application('Finder');
        const pb = $.NSPasteboard.generalPasteboard;
        // Keep Finder's clipboard representations intact. A new copy invalidates this token.
        const statePath = $.NSHomeDirectory().stringByAppendingPathComponent('.config/winmac-keyboard/pending-move');
        function pendingMove() {
            const token = $.NSString.stringWithContentsOfFileEncodingError(statePath, $.NSUTF8StringEncoding, null);
            return token && ObjC.unwrap(token) === String(Number(pb.changeCount));
        }
        function saveMove(value) {
            if (!$(value).writeToFileAtomicallyEncodingError(statePath, true, $.NSUTF8StringEncoding, null)) {
                throw new Error('WinMac: cannot write pending move state');
            }
        }
        function frontmost() { return finder.frontmost(); }
        function press(code, mods) {
            if (!frontmost()) return;
            stage = 'send key';
            se.keyCode(code, {using: mods || []});
        }
        if (!frontmost()) return;
        // Fail closed when Accessibility cannot establish the focused element.
        stage = 'focused element';
        let element = se.processes.byName('Finder').attributes.byName('AXFocusedUIElement').value();
        let editing = false;
        let fileView = false;
        for (let depth = 0; element && depth < 12; depth++) {
            stage = 'focused element role';
            const role = element.attributes.byName('AXRole').value();
            if (['AXTextField', 'AXTextArea', 'AXComboBox'].indexOf(role) >= 0) {
                editing = true;
                break;
            }
            if (['AXOutline', 'AXBrowser', 'AXList', 'AXTable', 'AXScrollArea'].indexOf(role) >= 0) fileView = true;
            if (role === 'AXWindow' || role === 'AXApplication') break;
            stage = 'focused element parent';
            element = element.attributes.byName('AXParent').value();
        }
        function clearMove() {
            saveMove('');
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
            const move = pendingMove();
            clearMove();
            press(9, move ? ['command down', 'option down'] : ['command down']);
            return;
        }
        if (finder.selection().length === 0) return;
        clearMove();
        if (action === 'cut') {
            const before = Number(pb.changeCount);
            press(8, ['command down']);
            let last = before;
            let stable = 0;
            for (let n = 0; n < 50; n++) {
                delay(0.02);
                const current = Number(pb.changeCount);
                stable = current !== before && current === last ? stable + 1 : 0;
                last = current;
                if (stable >= 5) break;
            }
            if (frontmost() && stable >= 5) saveMove(String(last));
        } else if (action === 'trash') press(51, ['command down']);
        else if (action === 'delete') press(51, ['command down', 'option down']);
        else if (action === 'rename') press(36);
    } catch (error) {
        throw new Error('WinMac Finder ' + stage + ': ' + error);
    }
}
