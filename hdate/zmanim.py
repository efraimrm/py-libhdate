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
from hdate.common import BaseClass
from hdate.date import HDate

try:
    from astral import Location
except ImportError:
    from hdate.common import Location

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

    def __unicode__(self):
        """Return a Unicode representation of Zmanim."""
        return u"".join(
            [
                u"{} - {}\n".format(
                    zman.description[self.hebrew], self.zmanim[zman.zman].time()
                )
                for zman in htables.ZMANIM
            ]
        )

    def __repr__(self):
        """Return a representation of Zmanim for programmatic use."""
        # As time zone information is not really reusable due to DST, when
        # creating a __repr__ of zmanim, we show a timezone naive datetime.
        return "Zmanim(date={}, location={}, hebrew={})".format(
            repr(self.time.astimezone(self.location.timezone).replace(tzinfo=None)),
            repr(self.location),
            self.hebrew,
        )

    @property
    def utc_zmanim(self):
        """Return a dictionary of the zmanim in UTC time format."""
        basetime = dt.datetime.combine(self.date, dt.time()).replace(tzinfo=pytz.utc)
        _LOGGER.debug("Calculating UTC zmanim for %r", basetime)
        return {
            key: basetime + dt.timedelta(minutes=value)
            for key, value in self.get_utc_sun_time_full().items()
        }

    @property
    def zmanim(self):
        """Return a dictionary of the zmanim the object represents."""
        return {
            key: value.astimezone(self.location.timezone)
            for key, value in self.utc_zmanim.items()
        }

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
            return self.zmanim["sunset"] - dt.timedelta(
                minutes=self.candle_lighting_offset
            )
        return None

    @property
    def _havdalah_datetime(self):
        """Compute the havdalah time based on settings."""
        if self.havdalah_offset == 0:
            return self.zmanim["three_stars"]
        # Otherwise, use the offset.
        return self.zmanim["sunset"] + dt.timedelta(minutes=self.havdalah_offset)

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

    @property
    def zmanim(self):
        """Return a dictionary of the zmanim the object represents."""
        # sunset and rise time
        sunrise = self.location.time_at_elevation(
            90.833, Location.SUN_RISING, self.date)
        sunset = self.location.time_at_elevation(
            90.833, Location.SUN_SETTING, self.date)

        _LOGGER.debug("Total seconds of light: %d",
                      (sunset - sunrise).total_seconds())

        # shaa zmanit by gra, 1/12 of light time
        sun_hour = (sunset - sunrise).total_seconds() / 3600 / 12
        midday = sunrise + ((sunset - sunrise) / 2)

        # get times of the different sun angles
        first_light = self.location.time_at_elevation(
            106.1, Location.SUN_RISING, self.date)
        talit = self.location.time_at_elevation(
            101.0, Location.SUN_RISING, self.date)
        first_stars = self.location.time_at_elevation(
            96.0, Location.SUN_SETTING, self.date)
        three_stars = self.location.time_at_elevation(
            98.5, Location.SUN_SETTING, self.date)
        mga_sunhour = (midday - first_light).total_seconds() / 3600 / 6

        _LOGGER.debug("Shaa zmanit according to GRA: %f", sun_hour)
        _LOGGER.debug("Shaa zmanit according to MGA: %f", mga_sunhour)

        res = dict(
            sunrise=sunrise, sunset=sunset, sun_hour=sun_hour,
            midday=midday, first_light=first_light, talit=talit,
            first_stars=first_stars, three_stars=three_stars,
            plag_mincha=sunset - dt.timedelta(hours=1.25 * sun_hour),
            stars_out=sunset + dt.timedelta(minutes=18. * sun_hour / 60.),
            small_mincha=sunrise + dt.timedelta(hours=9.5 * sun_hour),
            big_mincha=sunrise + dt.timedelta(hours=6.5 * sun_hour),
            mga_end_shma=first_light + dt.timedelta(hours=mga_sunhour * 3.),
            gra_end_shma=sunrise + dt.timedelta(hours=sun_hour * 3.),
            mga_end_tfila=first_light + dt.timedelta(hours=mga_sunhour * 4.),
            gra_end_tfila=sunrise + dt.timedelta(hours=sun_hour * 4.),
            midnight=midday + dt.timedelta(minutes=12 * 60.))
        return res
