// kpopmenu -- Kofoto popup menu.

function kpopSetupMenu(linkid, menuid)
{
    link = document.getElementById(linkid);
    link.addEventListener("click", function(event) { kpopHandleMenuLinkClick(event, menuid); }, false);
}

function kpopHandleMenuLinkClick(event, menuid)
{
    menu = document.getElementById(menuid);
    menu.addEventListener("mouseout", kpopHandleMenuMouseOut, false);
    menu.addEventListener("mouseover", kpopHandleMenuMouseOver, false);
    menu.style.left = event.clientX + "px";
    menu.style.top = event.clientY + "px";
    menu.style.visibility = "visible";
    linkid = event.currentTarget.id;
    a = linkid.match(/_([^_]+)$/);
    if (a.length > 1) {
        arg = a[1];
    } else {
        arg = null;
    }
    for (i = 0; i < menu.childNodes.length; ++i) {
        n = menu.childNodes[i];
        if (n.tagName && n.tagName.toLowerCase() == "li") {
            n.innerHTML = n.innerHTML.replace(/kpopid=\w*/, "kpopid=" + arg);
        }
    }
}

function kpopIsDescendantOf(x, y)
{
    if (x.parentNode) {
        if (x.parentNode == y) {
            return true;
        } else {
            return kpopIsDescendantOf(x.parentNode, y);
        }
    } else {
        return false;
    }
}

function kpopHandleMenuMouseOut(event)
{
    if (!kpopIsDescendantOf(event.relatedTarget, event.currentTarget)) {
        menu = event.currentTarget;
        window.hideTimeoutId = window.setTimeout("kpopHideMenu('" + menu.id + "')", 500);
    }
}

function kpopHandleMenuMouseOver(event)
{
    // The cursor is back in the menu again.
    if (window.hideTimeoutId) {
        window.clearTimeout(window.hideTimeoutId);
    }
}

function kpopHideMenu(menuid)
{
    menu = document.getElementById(menuid);
    menu.style.visibility = "hidden";
    menu.removeEventListener("mouseout", kpopHandleMenuMouseOut, false);
    window.hideTimeoutId = null;
}
