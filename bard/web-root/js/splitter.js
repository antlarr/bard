(function () {
function sdrag(onDrag, onStop, direction) {
        var startX = 0;
        var startY = 0;
        var el = this;
        var dragging = false;

        function move(e) {
            console.log('move');
            var fix = {};
            onDrag && onDrag(el, e.pageX, startX, e.pageY, startY, fix);
            if ('vertical' !== direction) {
                var pageX = ('pageX' in fix) ? fix.pageX : e.pageX;
                if ('startX' in fix) {
                    startX = fix.startX;
                }
                if (false === ('skipX' in fix)) {
                    el.style.left = (pageX - startX) + 'px';
                }
            }
            if ('horizontal' !== direction) {
                var pageY = ('pageY' in fix) ? fix.pageY : e.pageY;
                if ('startY' in fix) {
                    startY = fix.startY;
                }
                if (false === ('skipY' in fix)) {
                    el.style.top = (pageY - startY) + 'px';
                }
            }
        }

        function startDragging(e) {
            if (e.button != 0)
                return;
            console.log('start dragging');
            if (e.currentTarget instanceof HTMLElement || e.currentTarget instanceof SVGElement) {
                dragging = true;
                var left = el.style.left ? parseInt(el.style.left) : 0;
                var top = el.style.top ? parseInt(el.style.top) : 0;
                startX = e.pageX - left;
                startY = e.pageY - top;
                window.addEventListener('mousemove', move);
                document.body.style.cursor = "col-resize";
            }
            else {
                throw new Error("Your target must be an html element");
            }
        }

        this.addEventListener('mousedown', startDragging);

        window.addEventListener('mouseup', function (e) {
            document.body.style.cursor = "auto";
            if (true === dragging) {
                dragging = false;
                window.removeEventListener('mousemove', move);
                onStop && onStop(el, e.pageX, startX, e.pageY, startY);
            }
        });
    }
    Element.prototype.sdrag = sdrag;
})();

 var leftLimit = 0;
 var rightLimit = 100;
 var leftPane = document.getElementsByClassName("left-pane")[0];
 var rightPane = document.getElementsByClassName("right-pane")[0];
 var paneSep = document.getElementById('divider');

 paneSep.sdrag(function (el, pageX, startX, pageY, startY, fix) {

        fix.skipX = true;

        if (pageX < window.innerWidth * leftLimit / 100) {
            pageX = window.innerWidth * leftLimit / 100;
            fix.pageX = pageX;
        }
        if (pageX > window.innerWidth * rightLimit / 100) {
            pageX = window.innerWidth * rightLimit / 100;
            fix.pageX = pageX;
        }

        var cur = pageX / window.innerWidth * 100;
        if (cur < 0) {
            cur = 0;
        }
        if (cur > window.innerWidth) {
            cur = window.innerWidth;
        }


        var right = (100-cur-2);
        leftPane.style.width = cur + '%';
        rightPane.style.width = right + '%';

    }, null, 'horizontal');
