/**
 * For each touch, stores (indexed by the touch identifier) the element last hovered over
 */
var current_touches = {};


/**
 * Stores the filter and drop handlers for each drop area, indexed by the element id.
 *
 * The filter handler is a function that accepts one parameter with a list of types
 * being dragged over a drop area and returns true if it accepts the list of types,
 * or false if it doesn't accept it.
 *
 * The drop handler is a function that accepts three parameters, the element where
 * the drop is happening, a dictionary with the data being dropped and some dropArea
 * data set in the setDropArea call.
 */
var drop_handlers = {};

// Log functions
var log_count=0;
var prev_log = '';
function log(txt)
{
   log_count=log_count + 1;
   var cur_log = log_count + ' ' + txt;
   var msg = prev_log + '<br>' + cur_log;
   var log_element = $('#log');
   if (log_element) {
       log_element.html(msg);
   }
   prev_log = cur_log;
}


function setDraggable(el, data)
{
   el.addClass('draggable');
   el.attr('draggable',true);
   el.on('dragstart', function(evt) {
      for (var key in data) {
         if (evt && evt.originalEvent && 'dataTransfer' in evt.originalEvent)
         {
             evt.originalEvent.dataTransfer.setData(key, data[key]);
         }
         evt.originalEvent.bard_drag = true;
      };
      log('dragstart');
   });

   el.on('touchmove', function(e) {
      if(e.type == 'touchstart' || e.type == 'touchmove' || e.type == 'touchend' || e.type == 'touchcancel'){
          var touch = e.originalEvent.touches[0] || e.originalEvent.changedTouches[0];
          x = touch.pageX;
          y = touch.pageY;
          id = touch.identifier;
      } else if (e.type == 'mousedown' || e.type == 'mouseup' || e.type == 'mousemove' || e.type == 'mouseover'|| e.type=='mouseout' || e.type=='mouseenter' || e.type=='mouseleave') {
          x = e.clientX;
          y = e.clientY;
      }
      hover_element = document.elementFromPoint(x, y);
      if (current_touches.hasOwnProperty(id))
      {
          phover_element = current_touches[id];
      } else {
          phover_element = null;
          log('starting touchmove');
      };

      if (phover_element && phover_element != hover_element)
      {
          phover_element.classList.remove('dragover');
          delete current_touches[id];
      }

      if (hover_element.classList.contains('dropArea')) {
          handlers = drop_handlers[hover_element.id];
          if (handlers['filter'](Object.keys(data)))
          {
              hover_element.classList.add('dragover');
              current_touches[id] = hover_element;
          }
      }
      else
      {
          current_touches[id] = null;
      }

      e.preventDefault();
      return false;
   });

   el.on('touchend touchcancel', function(e) {
      if(e.type == 'touchstart' || e.type == 'touchmove' || e.type == 'touchend' || e.type == 'touchcancel'){
          var touch = e.originalEvent.changedTouches[0];
          x = touch.pageX;
          y = touch.pageY;
          id = touch.identifier;
      }

      if (!current_touches.hasOwnProperty(id))
      {
          return true;
      }

      delete current_touches[id];
      if (e.type == 'touchcancel') {
          return false;
      }
      hover_element = document.elementFromPoint(x, y);
      hover_element.classList.remove('dragover');

      log('drop over ' + hover_element.id);
      if (hover_element.classList.contains('dropArea')) {
          handlers = drop_handlers[hover_element.id];
          if (handlers['filter'](Object.keys(data)))
          {
              handlers['drop'](hover_element, data, handlers['data']);
              log('dropped');
          }
      }
      return false;
    });
}

function setDropArea(el, filter_func, drop_func, dropAreaData)
{
   el.addClass('dropArea');
   drop_handlers[el.attr('id')] = { 'filter': filter_func, 'drop': drop_func, 'data': dropAreaData};

   el.on('dragenter', function(evt) {
      log('drag enter');
      evt.preventDefault();
      evt.stopPropagation();
      if (!playlist_drop_filter(evt.originalEvent.dataTransfer.types))
          return;
      el.addClass("dragover");
   });

   el.on('dragleave', function(evt) {
      evt.preventDefault();
      el.removeClass("dragover");
   });

   el.on('dragover', function(evt) {
      evt.preventDefault();
   });

   el.on('drop', function(evt) {
      evt.preventDefault();
      if (!filter_func(evt.originalEvent.dataTransfer.types))
          return;
      el.removeClass("dragover");
//var i=0; i< evt.originalEvent.dataTransfer.items.length; i++)
      data = {}
      for (var i in evt.originalEvent.dataTransfer.types)
      {
//        console.log("... items[" + i + "].kind = " + evt.originalEvent.dataTransfer.items[i].kind + " ; type = " + evt.originalEvent.dataTransfer.items[i].type);
          key = evt.originalEvent.dataTransfer.types[i];
//        console.log("dropped mime:" + key);
          data[key] = evt.originalEvent.dataTransfer.getData(key);
      }

      drop_func(el, data, dropAreaData);
   });
}

/*
function playlist_drop_filter(types)
{
   return types.includes('application/x-bard');
}

function playlist_drop_handler(el, droppedData, dropAreaData)
{
      var data = droppedData["text/plain"];
      $(el).html(data);
      log('Dropped ' + droppedData['application/x-bard'] + ' to pl ' + dropAreaData['playlistID']);
}


setDraggable($( "#s1" ), {'text/plain': 'test', 'application/x-bard': '{"songID": 4}'});
setDraggable($( "#s2" ), {'text/plain': 'test2', 'application/x-bard': '{"songID": 5}'});
setDraggable($( "#s3" ), {'text/plain': 'test3', 'application/x-bard': '{"songID": 6}'});


setDropArea($( "#pl1" ), playlist_drop_filter, playlist_drop_handler, {'playlistID': 1});
setDropArea($( "#pl2" ), playlist_drop_filter, playlist_drop_handler, {'playlistID': 2});
setDropArea($( "#pl3" ), playlist_drop_filter, playlist_drop_handler, {'playlistID': 3});
*/
