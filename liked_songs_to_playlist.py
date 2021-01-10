import spotipy
import argparse
from spotipy.oauth2 import SpotifyOAuth

SCOPES = "user-library-read user-library-modify playlist-modify-public"
LIMIT = 50


class SpotifyLikedToPlaylist:
    def __init__(self, liked_playlist_name, scopes):
        self.liked_playlist_name = liked_playlist_name
        self.liked_playlist_id = None
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scopes))
        self.liked_songs = self.get_liked_songs()

    def sync(self, clobber=False):
        self.get_playlist_id()

        if self.liked_playlist_id:
            if clobber:
                self.clobber()
            else:
                self.liked_songs = self.get_missing_songs()
        else:
            self.create_playlist()
            self.get_playlist_id()

        self.add_songs_to_playlist()

    def create_playlist(self):
        user_id = self.sp.me()['id']
        self.sp.user_playlist_create(user_id, self.liked_playlist_name)

    def get_missing_songs(self):
        playlist_songs = self.get_playlist_songs()
        missing_songs = []

        for song in self.liked_songs:
            if song not in playlist_songs:
                missing_songs.append(song)

        return missing_songs

    def get_playlist_songs(self):
        offset = 0
        songs = []
        results = self.sp.playlist_items(self.liked_playlist_id,
                                         offset=offset,
                                         fields='items.track.id, items.track.duration_ms, items.track.name,'
                                                'items.track.artists, total',
                                         additional_types=['track'])

        # Get all the tracks as there is a limit.
        while results['items']:
            for song in results['items']:
                songs.append(SpotifySong(song['track']))
            offset += LIMIT
            results = self.sp.playlist_items(self.liked_playlist_id,
                                             offset=offset,
                                             fields='items.track.id, items.track.duration_ms, items.track.name,'
                                                    'items.track.artists, total',
                                             additional_types=['track'])
        return songs

    def get_playlist_id(self):
        offset = 0
        results = self.sp.current_user_playlists(limit=50, offset=offset)

        # Get all the playlists as there is a limit.
        while results['items']:
            for playlist in results['items']:
                if playlist['name'] == self.liked_playlist_name:
                    self.liked_playlist_id = playlist['id']
                    return
            offset += LIMIT
            results = self.sp.current_user_playlists(limit=50, offset=offset)
        return None

    def get_liked_songs(self):
        offset = 0
        liked_songs = []
        results = self.sp.current_user_saved_tracks(limit=LIMIT, offset=offset)

        # Get all the tracks as there is a limit.
        # results['items'] = results['items'][::-1]
        while results['items']:
            for song in results['items']:
                liked_songs.append(SpotifySong(song['track']))
            offset += LIMIT
            results = self.sp.current_user_saved_tracks(limit=LIMIT, offset=offset)
        return liked_songs

    def add_songs_to_playlist(self):
        # extract just the ids from the list of tuples
        track_ids = []

        self.liked_songs.reverse()
        for song in self.liked_songs:
            track_ids.append(song.song_id)
        # reverse
        # track_ids = track_ids[::-1]
        # self.liked_songs.reverse()
        #
        song_limit = 100
        num_songs = len(track_ids)
        idx = 0
        while idx != num_songs:
            songs_left = num_songs - idx
            added = songs_left if songs_left < song_limit else song_limit
            tracks_to_add = track_ids[idx:idx + added]
            tracks_to_add.reverse()
            self.sp.playlist_add_items(self.liked_playlist_id, tracks_to_add, position=0)
            idx += added

    def clobber(self):
        songs = self.get_playlist_songs()

        track_ids = []
        for song in songs:
            track_ids.append(song.song_id)

        song_limit = 100
        num_songs = len(track_ids)
        idx = 0
        while idx != num_songs:
            songs_left = num_songs - idx
            added = songs_left if songs_left < song_limit else song_limit
            self.sp.playlist_remove_all_occurrences_of_items(self.liked_playlist_id, track_ids[idx:idx + added])
            idx += added

        return


class SpotifySong:
    def __init__(self, track=None, name=None, artists=None, duration_ms=None, song_id=None):
        if not track:
            self.name = name
            self.artists = artists
            self.duration_ms = duration_ms
            self.song_id = song_id
        else:
            self.name = track['name']
            self.artists = track['artists']
            self.song_id = track['id']
            self.duration_ms = track['duration_ms']

    def __eq__(self, other):
        return (self.name == other.name and
                self.artists == other.artists and
                self.duration_ms == other.duration_ms)


def main():
    args = get_args()

    sltpl = SpotifyLikedToPlaylist(liked_playlist_name=args.name, scopes=SCOPES)
    sltpl.sync(clobber=args.clobber)


def get_args():
    parser = argparse.ArgumentParser(description='Creates a Liked Songs playlist so '
                                                 'others can see it')
    parser.add_argument('-n', '--name', required=False, default="Liked Songs Playlist",
                        help='Name of Liked Songs playlist.')
    parser.add_argument('-c', '--clobber', required=False, default=False,
                        help='Whether the playlist will be cleared before re-syncing')
    return parser.parse_args()


if __name__ == '__main__':
    main()
