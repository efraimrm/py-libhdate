py-libhdate
===========

Jewish/Hebrew date and Zmanim in native python 2.7/3.x

Originally ported from libhdate, see http://libhdate.sourceforge.net/ for more details (including license)

.. code :: python

    >>> import hdate
    >>> import datetime
    >>> c = hdate.Location("פתח תקוה", 32.08707, 34.88747, "Asia/Jerusalem", 54)
    >>> z = hdate.Zmanim(date=datetime.date(2016, 4, 18), location=c)
    >>> print z

::

    עלות השחר - 04:53:00
    זמן טלית ותפילין - 05:19:00
    הנץ החמה - 06:09:00
    סוף זמן ק"ש מג"א - 08:46:15
    סוף זמן ק"ש הגר"א - 09:24:15
    סוף זמן תפילה מג"א - 10:04:00
    סוף זמן תפילה גר"א - 10:29:20
    חצות היום - 12:39:30
    מנחה גדולה - 13:12:02.500000
    מנחה קטנה - 16:27:17.500000
    פלג מנחה - 17:48:38.750000
    שקיעה - 19:10:00
    צאת הככבים - 19:35:00
    לילה - 19:48:00
    חצות הלילה - 00:39:30

.. code :: python

    >>> z = hdate.Zmanim(date=datetime.date(2016, 4, 18), location=c)
    >>> print z

::

    Alot HaShachar - 04:53:00
    Talit & Tefilin's time - 05:19:00
    Sunrise - 06:09:00
    Shema EOT MG"A - 08:46:15
    Shema EOT GR"A - 09:24:15
    Tefila EOT MG"A - 10:04:00
    Tefila EOT GR"A - 10:29:20
    Midday - 12:39:30
    Big Mincha - 13:12:02.500000
    Small Mincha - 16:27:17.500000
    Plag Mincha - 17:48:38.750000
    Sunset - 19:10:00
    First stars - 19:35:00
    Night - 19:48:00
    Midnight - 00:39:30

.. code :: python

    >>> h=hdate.HDate(datetime.date(2016, 4, 18), hebrew=False)
    >>> print h

::

    Monday 10 Nisan 5776

.. code :: python

    >>> h=hdate.HDate(datetime.date(2016, 4, 26), hebrew=True)
    >>> print h

::

    יום שלישי י"ח בניסן התשע"ו ג' בעומר חול המועד פסח
