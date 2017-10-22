import beets.ui
from beets import config
from beets.autotag.hooks import AlbumInfo, TrackInfo, Distance
from beets.plugins import BeetsPlugin
from beets.util import confit
from pygn import pygn

class GracenotePlugin(BeetsPlugin):

    def __init__(self):
        super(GracenotePlugin, self).__init__()
        self.config.add({
            'client_id': '567455925-03EACCD670BFFE1B9EB327775F2ED4BA',
            'source_weight': 0.5,
        })
        self.config['client_id'].redact = True
        self.client_id = None
        self.user_id = None
        self.register_listener('import_begin', self.setup)

    def setup(self, session=None):
        """Create the 'pygn_client' field. Authenticate if necessary.
        """
        self.client_id = self.config['client_id'].as_str()
        if self.client_id:
            self.user_id = pygn.register(self.client_id)

    def search(self, artist=None, album=None, track=None):
        return pygn.search(
            clientID=self.client_id,
            userID=self.user_id,
            artist=artist,
            album=album,
            track=track
        )

    def candidates(self, items, artist, album, va_likely):
        """Returns a list of AlbumInfo objects for Gracenote search result matching an album and
        artist (if not various)
        """
        if not self.user_id:
            return

        if va_likely:
            metadata = self.search(album=album)
        else:
            metadata = self.search(artist=artist, album=album)

        return [self.get_album_info(metadata)]

    def album_distance(self, items, album_info, mapping):
        """Returns the album distance.
        """
        dist = Distance()
        if album_info.data_source == 'Gracenote':
            dist.add('source', self.config['source_weight'].as_number())
        return dist

    def album_for_id(self, album_id):
        return None

    def track_for_id(self, track_id):
        return None

    def get_album_info(self, result):
        """Returns an AlbumInfo object given a Gracenote metadata dict.
        """

        if not all([
            result.get(k) for k in [
                'album_artist_name',
                'tracks',
                'album_gnid',
                'album_title'
            ]
        ]):
            self._log.warn(u"Release does not contain the required fields")
            return None

        album = result.get('album_title')
        album_id = result.get('album_gnid')
        artist = result.get('album_artist_name', '')
        artist_id = None
        tracks = self.get_tracks(result.get('tracks'))
        year = result.get('album_year')
        various_artist = artist.lower().strip().startswith('various')
        country = result.get('pkg_lang')

        if year is not None and year.isdecimal():
            year = int(year)

        return AlbumInfo(
            album,
            album_id,
            artist,
            artist_id,
            tracks,
            asin=None,
            albumtype=None,
            va=various_artist,
            year=year,
            month=None,
            day=None,
            label=None,
            mediums=None,
            artist_sort=None,
            releasegroup_id=None,
            catalognum=None,
            script=None,
            language=None,
            country=country,
            albumstatus=None,
            media=None,
            albumdisambig=None,
            artist_credit=None,
            original_year=None,
            original_month=None,
            original_day=None,
            data_source='Gracenote',
            data_url=None
        )

    def get_tracks(self, tracks, default_artist=""):
        """Returns a list of TrackInfo objects for a set of Gracenote tracks.
        """
        for track in tracks:
            track.setdefault('track_artist_name', default_artist)
        return list(map(self.get_track_info, tracks))

    def get_track_info(self, track, artist=None):
        """Given a dict of Gracenote track metadata, returns the TrackInfo object for that track."""
        title = track.get('track_title')
        track_id = track.get('track_gnid')
        index = track.get('track_number')
        artist = track.get('track_artist_name', artist)

        if index is not None and index.isdecimal():
            index = int(index)

        return TrackInfo(title, track_id, artist=artist, index=index)
