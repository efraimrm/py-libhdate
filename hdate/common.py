"""Small helper classes."""

import datetime as dt
import logging
import math
import sys

import pytz

from hdate.htables import Months
_LOGGER = logging.getLogger(__name__)
HebrewDate = namedtuple("HebrewDate", ["year", "month", "day"])


class BaseClass(object):  # pylint: disable=useless-object-inheritance
    """Implement basic functionality for all classes."""

    def __str__(self):
        """Return a string representation."""
        if sys.version_info.major < 3:
            # pylint: disable=undefined-variable
            # pylint-comment: When using python3 and up, unicode() is undefined
            return unicode(self).encode("utf-8")  # noqa: F821

        return self.__unicode__()

    def __unicode__(self):  # pragma: no cover
        """Implement the representation of the object."""

    def __eq__(self, other):
        """Override equality operator."""
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return False

    def __ne__(self, other):
        """Override inequality operator."""
        return not self.__eq__(other)


class HebrewDate(BaseClass):  # pylint: disable=too-few-public-methods
    """Define a Hebrew date object."""

    def __init__(self, year, month, day):
        """Initialize the Hebrew date object."""
        self.year = year
        self.month = month if isinstance(month, Months) else Months(month)
        self.day = day


class Location(BaseClass):
    """Define a geolocation for Zmanim calculations."""

    SUN_RISING = 0
    SUN_SETTING = 1

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        name="Jerusalem",
        latitude=31.778,
        longitude=35.235,
        timezone="Asia/Jerusalem",
        altitude=754,
        diaspora=False,
    ):
        """Initialitze the location object."""
        self._timezone = None
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = timezone
        self.altitude = altitude
        self.diaspora = diaspora

    def __repr__(self):
        """Return a representation of Location for programmatic use."""
        return (
            "Location(name='{}', latitude={}, longitude={}, "
            "timezone='{}', altitude={}, diaspora={})".format(
                self.name,
                self.latitude,
                self.longitude,
                self.timezone,
                self.altitude,
                self.diaspora,
            )
        )

    @property
    def timezone(self):
        """Return the timezone."""
        return self._timezone

    @timezone.setter
    def timezone(self, value):
        """Set the timezone."""
        self._timezone = (
            value if isinstance(value, datetime.tzinfo) else pytz.timezone(value)
        )

    def time_at_elevation(self, elevation, direction=SUN_RISING, date=None,
                          local=True):
        _LOGGER.debug("Calculating time at elevation: %f", elevation)
        rise_minutes, set_minutes = self._get_utc_sun_time_deg(elevation, date)
        _LOGGER.debug("Rise time: %d, Set time: %d", rise_minutes, set_minutes)
        result = rise_minutes if direction == self.SUN_RISING else set_minutes
        return self.minutes_to_datetime(date, result, local)

    def _get_utc_sun_time_deg(self, deg, date=None):
        """
        Return the times in minutes from 00:00 (utc) for a given sun altitude.

        This is done for a given sun altitude in sunrise `deg` degrees
        This function only works for altitudes sun really is.
        If the sun never gets to this altitude, the returned sunset and sunrise
        values will be negative. This can happen in low altitude when latitude
        is nearing the poles in winter times, the sun never goes very high in
        the sky there.

        Algorithm from
        http://www.srrb.noaa.gov/highlights/sunrise/calcdetails.html
        The low accuracy solar position equations are used.
        These routines are based on Jean Meeus's book Astronomical Algorithms.
        """
        gama = 0        # location of sun in yearly cycle in radians
        eqtime = 0      # difference betwen sun noon and clock noon
        decl = 0        # sun declanation
        hour_angle = 0  # solar hour angle
        sunrise_angle = math.pi * deg / 180.0  # sun angle at sunrise/set

        # get the day of year
        day_of_year = (date - dt.date(date.year, 1, 1)).days

        # get radians of sun orbit around earth =)
        gama = 2.0 * math.pi * ((day_of_year - 1) / 365.0)

        # get the diff betwen suns clock and wall clock in minutes
        eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(gama) -
                           0.032077 * math.sin(gama) -
                           0.014615 * math.cos(2.0 * gama) -
                           0.040849 * math.sin(2.0 * gama))

        # calculate suns declanation at the equater in radians
        decl = (0.006918 - 0.399912 * math.cos(gama) +
                0.070257 * math.sin(gama) -
                0.006758 * math.cos(2.0 * gama) +
                0.000907 * math.sin(2.0 * gama) -
                0.002697 * math.cos(3.0 * gama) +
                0.00148 * math.sin(3.0 * gama))

        # we use radians, ratio is 2pi/360
        latitude = math.pi * self.latitude / 180.0

        # the sun real time diff from noon at sunset/rise in radians
        try:
            hour_angle = (math.acos(
                math.cos(sunrise_angle) /
                (math.cos(latitude) * math.cos(decl)) -
                math.tan(latitude) * math.tan(decl)))
        # check for too high altitudes and return negative values
        except ValueError:
            return -720, -720

        # we use minutes, ratio is 1440min/2pi
        hour_angle = 720.0 * hour_angle / math.pi

        # get sunset/rise times in utc wall clock in minutes from 00:00 time
        # sunrise / sunset
        return int(720.0 - 4.0 * self.longitude - hour_angle - eqtime), \
            int(720.0 - 4.0 * self.longitude + hour_angle - eqtime)

    def minutes_to_datetime(self, date, minutes_from_utc, as_local=True):
        """Return the local time for a given time UTC."""
        from_zone = tz.gettz('UTC')
        to_zone = self.timezone
        utc = dt.datetime.combine(date, dt.time()) + \
            dt.timedelta(minutes=minutes_from_utc)
        utc = utc.replace(tzinfo=from_zone)
        local = utc.astimezone(to_zone)
        return local if as_local else utc
