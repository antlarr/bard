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

   this.seek = function(position) {
      this.media.currentTime = this.media.duration * position;
   };

   this.setVolume = function(volume) {
      this.media.volume = volume;
   };

   this.timeUpdated = function() {
      this.ui.updateTime(this.media.currentTime, this.media.duration);
   }

   this.media.addEventListener('timeupdate', this.timeUpdated.bind(this));
};

