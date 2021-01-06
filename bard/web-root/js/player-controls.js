function PlayerControls(playerBackend)
{
    this.name = 'PlayerControls';
    this.media = document.getElementById('player');
    this.progressBarContainer = document.getElementById("progress-bar-container");
    this.progressBar = document.getElementById('progress-bar');
    this.progressDot = document.getElementById('progress-dot');
    this.currentTimeSpan = document.getElementById('current-time');
    this.songDurationSpan = document.getElementById('song-duration');
    this.volumeSlider = document.getElementById('volume');
    this.player = null;
    this.enabled = null;

    this.prevSong = function() {
        bard.requestPrevSong();
    };

    this.nextSong = function() {
        bard.requestNextSong();
    };

    $("#prevSongButton").on("click", this.prevSong.bind(this));
    $("#nextSongButton").on("click", this.nextSong.bind(this));

    this.setPlayIcon = function(iconName) {
        document.getElementById('playPauseSongButton').style.backgroundImage = 'url(\'/static/images/' + iconName + '.png\')';
    }
    this.play = function() {
        this.player.play();
        this.setPlayIcon('media-playback-pause');
        if ('mediaSession' in navigator)
            navigator.mediaSession.playbackState = "playing";
    }
    this.pause = function() {
        this.player.pause();
        this.setPlayIcon('media-playback-start');
        if ('mediaSession' in navigator)
            navigator.mediaSession.playbackState = "paused";
    }
    this.playPause = function() {
        if (!this.enabled) {
            return;
        }

        if (this.media.paused) {
            this.play();
        } else {
            this.pause();
        }
    };

    this.setEnable = function(enable) {
        if (enable) {
            this.setPlayIcon('media-playback-pause');
        } else {
            this.setPlayIcon('media-playback-stop');
        };
        this.enabled = enable;
    };
    this.setEnable(false);

    this.stoppedPlaying = function() {
        if (this.enabled) {
            this.setPlayIcon('media-playback-start');
        } else {
            this.setPlayIcon('media-playback-stop');
        };
    }

    this.mouseUpOnProgressBar = function(ev) {
        var width = this.progressBarContainer.offsetWidth;
        var value = ev.pageX / width;
        this.player.seekPercentage(value);
    }

    this.seek = function(seekTime) {
        this.player.seekTo(seekTime);
    }

    this.seekBackward = function() {
        this.player.seekBackward();
    }

    this.seekForward = function() {
        this.player.seekForward();
    }

    this.updateTime = function(currentTime, duration) {
        this.currentTimeSpan.textContent = formatDurationValue(currentTime);
        var d = duration;
        if (isNaN(duration))
        {
            this.songDurationSpan.textContent = '--:--';
            d = 1000;
        }
        else
            this.songDurationSpan.textContent = formatDurationValue(duration);
        var barLength = 100 * (currentTime / duration);
        this.progressBar.style.width = barLength + '%';
        this.progressDot.style.left = barLength + '%';

        if ('mediaSession' in navigator) {
            navigator.mediaSession.setPositionState({
                duration: d,
                playbackRate: 1.0,
                position: currentTime
            });
        }
    };

    this.volumeSliderMoved = function(ev) {
        this.player.setVolume(this.volumeSlider.value / 100);
    };

    document.getElementById('playPauseSongButton').addEventListener('click', this.playPause.bind(this));
    //$("#playPauseSongButton").on("click", this.playPause);

    $("#progress-bar-container").on("mouseup", this.mouseUpOnProgressBar.bind(this));
    $("#volume").on("input", this.volumeSliderMoved.bind(this));

    this.test = function() {
        alert('testing ' + this.player);
    };

    this.recalcMaxWidths = function() {
        var width = document.body.clientWidth / 2 - 80;
        document.getElementById("current-song-info").style.maxWidth = width + "px";
        document.getElementById("media-status").style.maxWidth = width + "px";
    };

    window.addEventListener("resize", this.recalcMaxWidths.bind(this));
    this.recalcMaxWidths();

    if ('mediaSession' in navigator) {
        navigator.mediaSession.setActionHandler('play', this.play.bind(this));
        navigator.mediaSession.setActionHandler('pause', this.pause.bind(this));
        navigator.mediaSession.setActionHandler('stop', this.pause.bind(this));
        navigator.mediaSession.setActionHandler('seekbackward', this.seekBackward.bind(this));
        navigator.mediaSession.setActionHandler('seekforward', this.seekForward.bind(this));
        navigator.mediaSession.setActionHandler('seekto', function(details) { this.seek(details.seekTime); }.bind(this));
        navigator.mediaSession.setActionHandler('previoustrack', this.prevSong.bind(this));
        navigator.mediaSession.setActionHandler('nexttrack', this.nextSong.bind(this));

    }

}
