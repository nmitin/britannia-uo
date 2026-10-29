for (const w of workspace.windowList()) {
    const rc = "" + w.resourceClass;
    if (rc.toLowerCase().indexOf("classicuo") >= 0 || ("" + w.caption).toLowerCase().indexOf("ultima") >= 0)
        print("CUO:", rc, "|", w.caption, "| minimized:", w.minimized);
}
