"""Methods for going back and forth between various calendars."""


def get_chalakim(hours, parts):
    """Return the number of total parts (chalakim)."""
    return (hours * PARTS_IN_HOUR) + parts


PARTS_IN_HOUR = 1080
PARTS_IN_DAY = 24 * PARTS_IN_HOUR
PARTS_IN_WEEK = 7 * PARTS_IN_DAY
PARTS_IN_MONTH = PARTS_IN_DAY + get_chalakim(12, 793)  # Fix for regular month


def _days_from_3744(hebrew_year):
    """Return: Number of days since 3,1,3744."""
    # Start point for calculation is Molad new year 3744 (16BC)
    years_from_3744 = hebrew_year - 3744
    molad_3744 = get_chalakim(1 + 6, 779)    # Molad 3744 + 6 hours in parts

    # Time in months
    leap_months = (years_from_3744 * 7 + 1) / 19  # Number of leap months
    leap_left = (years_from_3744 * 7 + 1) % 19    # Months left of leap cycle
    months = years_from_3744 * 12 + leap_months   # Total Number of months

    # Time in parts and days
    # Molad This year + Molad 3744 - corrections
    parts = months * PARTS_IN_MONTH + molad_3744
    # 28 days in month + corrections
    days = months * 28 + parts / PARTS_IN_DAY - 2

    # Time left for round date in corrections
    # 28 % 7 = 0 so only corrections counts
    parts_left_in_week = parts % PARTS_IN_WEEK
    parts_left_in_day = parts % PARTS_IN_DAY
    week_day = parts_left_in_week / PARTS_IN_DAY

    # Special cases of Molad Zaken
    if ((leap_left < 12 and week_day == 3 and
         parts_left_in_day >= get_chalakim(9 + 6, 204)) or
            (leap_left < 7 and week_day == 2 and
             parts_left_in_day >= get_chalakim(15 + 6, 589))):
        days += 1
        week_day += 1

    # ADU
    if week_day == 1 or week_day == 4 or week_day == 6:
        days += 1

    return days


def _get_size_of_hebrew_year(hebrew_year):
    """Return: total days in hebrew year."""
    return _days_from_3744(hebrew_year + 1) - _days_from_3744(hebrew_year)


def get_year_type(size_of_year, new_year_dw):
    """
    Return: type of the year.

    Args:
    size_of_year: Length of year in days
    new_year_dw First week day of year
    table:
    year type | year length | Tishery 1 day of week
    | 1       | 353         | 2
    | 2       | 353         | 7
    | 3       | 354         | 3
    | 4       | 354         | 5
    | 5       | 355         | 2
    | 6       | 355         | 5
    | 7       | 355         | 7
    | 8       | 383         | 2
    | 9       | 383         | 5
    |10       | 383         | 7
    |11       | 384         | 3
    |12       | 385         | 2
    |13       | 385         | 5
    |14       | 385         | 7
    """
    # Only 14 combinations of size and week day are posible
    year_types = [1, 0, 0, 2, 0, 3, 4,
                  0, 5, 0, 6, 7, 8, 0,
                  9, 10, 0, 11, 0, 0, 12,
                  0, 13, 14]

    # convert size and first day to 1..24 number
    # 2,3,5,7 -> 1,2,3,4
    # 353, 354, 355, 383, 384, 385 -> 0, 1, 2, 3, 4, 5
    offset = (new_year_dw + 1) / 2
    offset = offset + 4 * ((size_of_year % 10 - 3) + (size_of_year / 10 - 35))

    return year_types[offset - 1]


def gdate_to_jd(day, month, year):
    """
    Compute Julian day from Gregorian day, month and year.

    Algorithm from wikipedia's julian_day article.
    Return: The julian day number
    """
    not_jan_or_feb = (14 - month) / 12
    year_since_4800bc = year + 4800 - not_jan_or_feb
    month_since_4800bc = month + 12 * not_jan_or_feb - 3
    jdn = day + (153 * month_since_4800bc + 2) / 5 + 365 * year_since_4800bc \
        + (year_since_4800bc / 4 - year_since_4800bc / 100 +
           year_since_4800bc / 400) - 32045
    return jdn


def hdate_to_jd(day, month, year):
    """
    Compute Julian day from Hebrew day, month and year.

    Return: julian day number,
            1 of tishrey julians,
            1 of tishrey julians next year
    """
    if month == 13:
        month = 6
    if month == 14:
        month = 6
        day += 30

    # Calculate days since 1,1,3744
    days_from_3744 = _days_from_3744(year)
    day = days_from_3744 + (59 * (month - 1) + 1) / 2 + day

    # length of year
    length_of_year = _days_from_3744(year + 1) - days_from_3744
    # Special cases for this year
    if length_of_year % 10 > 4 and month > 2:  # long Heshvan
        day += 1
    if length_of_year % 10 < 4 and month > 3:  # short Kislev
        day -= 1
    if length_of_year > 365 and month > 6:  # leap year
        day += 30

    # adjust to julian
    jday = day + 1715118
    jd_tishrey1 = days_from_3744 + 1715119
    jd_tishrey1_next_year = jd_tishrey1 + length_of_year

    return jday, jd_tishrey1, jd_tishrey1_next_year


def jd_to_gdate(jday):
    """
    Convert from the Julian day to the Gregorian day.

    Algorithm from 'Julian and Gregorian Day Numbers' by Peter Meyer.
    Return: day, month, year
    """
    # pylint: disable=invalid-name

    # The algorithm is a verbatim copy from Peter Meyer's article
    # No explanation in the article is given for the variables
    # Hence the exception for pylint

    l = jday + 68569
    n = (4 * l) / 146097
    l = l - (146097 * n + 3) / 4
    i = (4000 * (l + 1)) / 1461001  # that's 1,461,001
    l = l - (1461 * i) / 4 + 31
    j = (80 * l) / 2447
    day = l - (2447 * j) / 80
    l = j / 11
    month = j + 2 - (12 * l)
    year = 100 * (n - 49) + i + l  # that's a lower-case L

    return day, month, year


def jd_to_hdate(jday):
    """Convert from the Julian day to the Hebrew day."""
    # calculate Gregorian date
    day, month, year = jd_to_gdate(jday)

    # Guess Hebrew year is Gregorian year + 3760
    year = year + 3760

    jd_tishrey1 = _days_from_3744(year) + 1715119
    jd_tishrey1_next_year = _days_from_3744(year + 1) + 1715119

    # Check if computed year was underestimated
    if jd_tishrey1_next_year <= jday:
        year = year + 1
        jd_tishrey1 = jd_tishrey1_next_year
        jd_tishrey1_next_year = _days_from_3744(year + 1) + 1715119

    size_of_year = jd_tishrey1_next_year - jd_tishrey1

    # days into this year, first month 0..29
    days = jday - jd_tishrey1

    # last 8 months allways have 236 days
    if days >= (size_of_year - 236):  # in last 8 months
        days = days - (size_of_year - 236)
        month = days * 2 / 59
        day = days - (month * 59 + 1) / 2 + 1

        month = month + 4 + 1

        # if leap
        if size_of_year > 355 and month <= 6:
            month = month + 8
    else:  # in 4-5 first months
        # Special cases for this year
        if size_of_year % 10 > 4 and days == 59:   # long Heshvan (day 30)
            month = 1
            day = 30
        elif size_of_year % 10 > 4 and days > 59:  # long Heshvan
            month = (days - 1) * 2 / 59
            day = days - (month * 59 + 1) / 2
        elif size_of_year % 10 < 4 and days > 87:  # short kislev
            month = (days + 1) * 2 / 59
            day = days - (month * 59 + 1) / 2 + 2
        else:  # regular months
            month = days * 2 / 59
            day = days - (month * 59 + 1) / 2 + 1

        month = month + 1
    return day, month, year, jd_tishrey1, jd_tishrey1_next_year
