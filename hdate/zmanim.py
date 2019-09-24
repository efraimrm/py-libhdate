# -*- coding: utf-8 -*-

"""
Jewish calendrical times for a given location.

HDate calculates and generates a representation either in English or Hebrew
of the Jewish calendrical times for a given location
"""
from __future__ import division

import datetime as dt
import logging
import math

import pytz

from hdate import htables
from hdate.common import BaseClass, Location
from hdate.date import HDate

_LOGGER = logging.getLogger(__name__)


class Zmanim(BaseClass):
    """Return Jewish day times.

    The Zmanim class returns times for the specified day ONLY. If you wish to
    obtain times for the interval of a multi-day holiday for example, you need
    to use Zmanim in conjunction with some of the iterative properties of
    HDate. Also, Zmanim are reported regardless of the current time. So the
    havdalah value is constant if the current time is before or after it.
    The current time is only used to report the "issur_melacha_in_effect"
    property.
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        date=dt.datetime.now(),
        location=Location(),
        hebrew=True,
        candle_lighting_offset=18,
        havdalah_offset=0,
    ):
        """
        Initialize the Zmanim object.

        As the timezone is expected to be part of the location object, any
        tzinfo passed along is discarded. Essentially making the datetime
        object non-timezone aware.

        The time zone information is appended to the date received based on the
        location object. After which it is transformed to UTC for all internal
        calculations.
        """
        self.location = location
        self.hebrew = hebrew
        self.candle_lighting_offset = candle_lighting_offset
        self.havdalah_offset = havdalah_offset

        # If a non-timezone aware date is received, use timezone from location
        # to make it timezone aware and change to UTC for calculations.

        # If timezone aware is received as date, we expect it to match the
        # timezone specified by location, so it can be overridden and changed
        # to UTC for calculations as above.
        if isinstance(date, dt.datetime):
            _LOGGER.debug("Date input is of type datetime: %r", date)
            self.date = date.date()
            self.time = date.replace(tzinfo=None)
        elif isinstance(date, dt.date):
            _LOGGER.debug("Date input is of type date: %r", date)
            self.date = date
            self.time = dt.datetime.now()
        else:
            raise TypeError

        _LOGGER.debug("Resetting timezone to UTC for calculations")
        self.time = location.timezone.localize(self.time).astimezone(pytz.utc)

        self.sunrise, self.sunset = self._get_utc_sun_time_deg(90.8333)

    def __unicode__(self):
        """Return a Unicode representation of Zmanim."""
        return u"".join([
            u"{} - {}\n".format(
                zman.description[self.hebrew],
                self.zmanim(zman.zman).time()) for zman in htables.ZMANIM])

    def __repr__(self):
        """Return a representation of Zmanim for programmatic use."""
        # As time zone information is not really reusable due to DST, when
        # creating a __repr__ of zmanim, we show a timezone naive datetime.
        return "Zmanim(date={}, location={}, hebrew={})".format(
            repr(self.time.astimezone(self.location.timezone).replace(tzinfo=None)),
            repr(self.location),
            self.hebrew,
        )

    def __getattr__(self, key):
        """"Sanitize getattr calls to only allow zmanim keys."""
        if key in any([zman.zman for zman in htables.ZMANIM]):
            return getattr(self, key)
        else:
            raise AttributeError("%s is not a valid zman", key)

    def utc_zman(self, key):
        """Return the zman value in UTC time format for the given key."""
        basetime = dt.datetime.combine(self.date, dt.time()).replace(
            tzinfo=pytz.utc)
        _LOGGER.debug("Calculating UTC zmanim for %r", basetime)
        
        return basetime + dt.timedelta(minutes=getattr(self, key))

    def zmanim(self, key):
        """Return the zman value for the given key."""
        return utc_zman(key).astimezone(self.location.timezone)

    @property
    def candle_lighting(self):
        """Return the time for candle lighting, or None if not applicable."""
        today = HDate(gdate=self.date, diaspora=self.location.diaspora)
        tomorrow = HDate(
            gdate=self.date + dt.timedelta(days=1), diaspora=self.location.diaspora
        )

        # If today is a Yom Tov or Shabbat, and tomorrow is a Yom Tov or
        # Shabbat return the havdalah time as the candle lighting time.
        if (today.is_yom_tov or today.is_shabbat) and (
            tomorrow.is_yom_tov or tomorrow.is_shabbat
        ):
            return self._havdalah_datetime

        # Otherwise, if today is Friday or erev Yom Tov, return candle
        # lighting.
        if tomorrow.is_shabbat or tomorrow.is_yom_tov:
            return (self.zmanim("sunset")
                    - dt.timedelta(minutes=self.candle_lighting_offset))
        return None

    @property
    def _havdalah_datetime(self):
        """Compute the havdalah time based on settings."""
        if self.havdalah_offset == 0:
            return self.zmanim("motsei_shabbat")
        # Otherwise, use the offset.
        return (self.zmanim("sunset")
                + dt.timedelta(minutes=self.havdalah_offset))

    @property
    def havdalah(self):
        """Return the time for havdalah, or None if not applicable.

        If havdalah_offset is 0, uses the time for three_stars. Otherwise,
        adds the offset to the time of sunset and uses that.
        If it's currently a multi-day YomTov, and the end of the stretch is
        after today, the havdalah value is defined to be None (to avoid
        misleading the user that melacha is permitted).
        """
        today = HDate(gdate=self.date, diaspora=self.location.diaspora)
        tomorrow = HDate(
            gdate=self.date + dt.timedelta(days=1), diaspora=self.location.diaspora
        )

        # If today is Yom Tov or Shabbat, and tomorrow is Yom Tov or Shabbat,
        # then there is no havdalah value for today. Technically, there is
        # havdalah mikodesh l'kodesh, but that is represented in the
        # candle_lighting value to avoid misuse of the havdalah API.
        if today.is_shabbat or today.is_yom_tov:
            if tomorrow.is_shabbat or tomorrow.is_yom_tov:
                return None
            return self._havdalah_datetime
        return None

    @property
    def issur_melacha_in_effect(self):
        """At the given time, return whether issur melacha is in effect."""
        today = HDate(gdate=self.date, diaspora=self.location.diaspora)
        tomorrow = HDate(
            gdate=self.date + dt.timedelta(days=1), diaspora=self.location.diaspora
        )

        if (today.is_shabbat or today.is_yom_tov) and (
            tomorrow.is_shabbat or tomorrow.is_yom_tov
        ):
            return True
        if (today.is_shabbat or today.is_yom_tov) and (self.time < self.havdalah):
            return True
        if (tomorrow.is_shabbat or tomorrow.is_yom_tov) and (
            self.time > self.candle_lighting
        ):
            return True

        return False

    def gday_of_year(self):
        """Return the number of days since January 1 of the given year."""
        return (self.date - dt.date(self.date.year, 1, 1)).days

    def _get_utc_sun_time_deg(self, deg):
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
        gama = 0  # location of sun in yearly cycle in radians
        eqtime = 0  # difference betwen sun noon and clock noon
        decl = 0  # sun declanation
        hour_angle = 0  # solar hour angle
        sunrise_angle = math.pi * deg / 180.0  # sun angle at sunrise/set

        # get the day of year
        day_of_year = self.gday_of_year()

        # get radians of sun orbit around earth =)
        gama = 2.0 * math.pi * ((day_of_year - 1) / 365.0)

        # get the diff betwen suns clock and wall clock in minutes
        eqtime = 229.18 * (
            0.000075
            + 0.001868 * math.cos(gama)
            - 0.032077 * math.sin(gama)
            - 0.014615 * math.cos(2.0 * gama)
            - 0.040849 * math.sin(2.0 * gama)
        )

        # calculate suns declanation at the equater in radians
        decl = (
            0.006918
            - 0.399912 * math.cos(gama)
            + 0.070257 * math.sin(gama)
            - 0.006758 * math.cos(2.0 * gama)
            + 0.000907 * math.sin(2.0 * gama)
            - 0.002697 * math.cos(3.0 * gama)
            + 0.00148 * math.sin(3.0 * gama)
        )

        # we use radians, ratio is 2pi/360
        latitude = math.pi * self.location.latitude / 180.0

        # the sun real time diff from noon at sunset/rise in radians
        try:
            hour_angle = math.acos(
                math.cos(sunrise_angle) / (math.cos(latitude) * math.cos(decl))
                - math.tan(latitude) * math.tan(decl)
            )
        # check for too high altitudes and return negative values
        except ValueError:
            return -720, -720

        # we use minutes, ratio is 1440min/2pi
        hour_angle = 720.0 * hour_angle / math.pi

        # get sunset/rise times in utc wall clock in minutes from 00:00 time
        # sunrise / sunset
        longitude = self.location.longitude
        return (
            int(720.0 - 4.0 * longitude - hour_angle - eqtime),
            int(720.0 - 4.0 * longitude + hour_angle - eqtime),
        )

    @property
    def shaa_zmanit_gra(self):
        return (self.sunset - self.sunrise) // 12

    @property
    def shaa_zmanit_mga(self):
        return (self.midday - self.alot_hashachar) / 6

    @property
    def midday(self):
        return (self.sunset + self.sunrise) // 2

    @property
    def alot_hashachar(self):
        result, _ = self._get_utc_sun_time_deg(106.1)
        return result
    
    @property
    def misheyakir(self):
        result, _ = self._get_utc_sun_time_deg(101.0)
        return result
    
    @property
    def tset_hakochavim(self):
        _, result = self._get_utc_sun_time_deg(96.0)
        return result
    
    @property
    def motsei_shabbat(self):
        _, result = self._get_utc_sun_time_deg(98.5)
        return result
    
    @property
    def plag_mincha(self):
        return self.sunset - 1.25 * self.shaa_zmanit_gra

    @property
    def stars_out(self):
        return self.sunset + 18. * self.shaa_zmanit_gra / 60.

    @property
    def mincha_ktana(self):
        return self.sunrise + 9.5 * self.shaa_zmanit_gra

    @property
    def mincha_gedola(self):
        return self.sunrise + 6.5 * self.shaa_zmanit_gra

    @property
    def end_shma_mga(self):
        return self.alot_hashachar + self.shaa_zmanit_mga * 3.

    @property
    def end_shma_gra(self):
        return self.sunrise + self.shaa_zmanit_gra * 3.

    @property
    def end_tfila_mga(self):
        return self.alot_hashachar + self.shaa_zmanit_mga * 4.

    @property
    def end_tfila_gra(self):
        return self.sunrise + self.shaa_zmanit_gra * 4.

    @property
    def midnight(self):
        return self.midday + 12 * 60.
