function WebPlayer() {
   this.name = 'WebPlayer';
   this.media = document.getElementById('player');
   this.ui = null;

   this.play = function() {
      var media = document.getElementById('player');
      media.play();
   };

   this.pause = function() {
      var media = document.getElementById('player');
      media.pause();
   };

   this.nextSong = function() {
   };

   this.prevSong = function() {
   };

   this.seekPercentage = function(position) {
      this.media.currentTime = this.media.duration * position;
   };

   this.seekTo = function(position) {
      if (position > this.media.duration)
          position = this.media.duration;
      this.media.currentTime = position;
   };

   this.seekBackward = function() {
      this.media.currentTime = this.media.currentTime - 5;
   }

   this.seekForward = function() {
      this.media.currentTime = this.media.currentTime + 5;
   }

   this.setVolume = function(volume) {
      this.media.volume = volume;
   };

   this.timeUpdated = function() {
      this.ui.updateTime(this.media.currentTime, this.media.duration);
   }

   this.media.addEventListener('timeupdate', this.timeUpdated.bind(this));
};

