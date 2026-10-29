const wins = workspace.windowList();
for (const w of wins) {
    print("WIN:", w.resourceClass, "|", w.caption);
    const rc = ("" + w.resourceClass).toLowerCase();
    const cap = ("" + w.caption).toLowerCase();
    if (rc.indexOf("classicuo") >= 0 || cap.indexOf("ultima") >= 0) {
        workspace.activeWindow = w;
        print("ACTIVATED:", w.caption);
    }
}
