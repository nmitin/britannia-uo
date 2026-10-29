const wins = workspace.windowList();
for (const w of wins) {
    const rc = ("" + w.resourceClass).toLowerCase();
    if (rc.indexOf("classicuo") < 0) continue;
    const cap = "" + w.caption;
    print("CUO WINDOW:", cap);
    if (cap.indexOf("[dev]") >= 0) {
        print("CLOSING OLD:", cap);
        w.close();
    } else {
        workspace.activeWindow = w;
        print("ACTIVATED GAME:", cap);
    }
}
