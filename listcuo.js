const wins = workspace.windowList();
for (const w of wins) {
    const rc = ("" + w.resourceClass).toLowerCase();
    if (rc.indexOf("classicuo") >= 0) {
        print("CUO:", w.caption, "min:", w.minimized, "geom:", w.geometry.x, w.geometry.y, w.geometry.width, w.geometry.height);
    }
}
