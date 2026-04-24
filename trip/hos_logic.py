# from datetime import datetime, timedelta

# # ============================================================
# # FMCSA HOS Constants — 70hr/8-day Property Carrier Rule
# # Source: FMCSA Interstate Truck Driver's Guide to Hours of Service (April 2022)
# # ============================================================
# MAX_DRIVING_HOURS   = 11.0   # § 395.3(a)(3) — max driving per shift
# MAX_WINDOW_HOURS    = 14.0   # § 395.3(a)(2) — 14-hour driving window
# MIN_REST_HOURS      = 10.0   # § 395.3(a)(1) — min consecutive off-duty
# MAX_CYCLE_HOURS     = 70.0   # § 395.3(b)    — 70hr/8-day limit
# BREAK_AFTER_HOURS   = 8.0    # § 395.3(a)(3)(ii) — 30-min break after 8 cumulative hrs
# BREAK_DURATION      = 0.5    # 30 minutes
# FUEL_INTERVAL_MILES = 1000.0 # Fuel stop every ≤1000 miles
# PICKUP_DURATION     = 1.0    # 1 hour on-duty not driving for pickup
# DROPOFF_DURATION    = 1.0    # 1 hour on-duty not driving for dropoff
# FUEL_STOP_DURATION  = 0.5    # 30 minutes for fueling


# def calculate_trip_schedule(current_location, pickup_location, dropoff_location,
#                              current_cycle_used, route_segments):
#     """
#     Calculate a fully FMCSA-compliant HOS trip schedule.

#     route_segments: [
#         {'from': 'Chicago, IL', 'to': 'Dallas, TX', 'distance_miles': 925, 'duration_hours': 16.8},
#         {'from': 'Dallas, TX',  'to': 'Los Angeles, CA', 'distance_miles': 1423, 'duration_hours': 25.9},
#     ]

#     Returns list of day objects:
#         day = {
#             'day_num': int,
#             'date_label': str,
#             'duty_periods': [{status, start_hour, end_hour, location, note}],
#             'remarks': [{hour, location, note}],        # only status changes
#             'totals': {off_duty, sleeper_berth, driving, on_duty_not_driving},
#             'miles_today': float,
#         }
#     """

#     # --------------------------------------------------------
#     # Step 1: Build flat event list in CORRECT order:
#     #   pre-trip → drive(current→pickup) → pickup → drive(pickup→dropoff) → dropoff
#     # --------------------------------------------------------
#     schedule_events = []

#     for seg_idx, segment in enumerate(route_segments):
#         seg_miles   = segment['distance_miles']
#         seg_hours   = segment['duration_hours']
#         seg_from    = segment['from']
#         seg_to      = segment['to']

#         # Split segment into drive chunks with fuel stops
#         miles_driven   = 0.0
#         miles_since_fuel = 0.0

#         while miles_driven < seg_miles:
#             miles_to_fuel    = FUEL_INTERVAL_MILES - miles_since_fuel
#             miles_remaining  = seg_miles - miles_driven
#             chunk_miles      = min(miles_to_fuel, miles_remaining)
#             chunk_hours      = (chunk_miles / seg_miles) * seg_hours
#             is_final_chunk   = (miles_driven + chunk_miles >= seg_miles - 0.01)

#             # Location label: where you are HEADING toward
#             drive_location = seg_to if is_final_chunk else seg_from

#             schedule_events.append({
#                 'type':     'drive',
#                 'duration': chunk_hours,
#                 'miles':    chunk_miles,
#                 'location': drive_location,
#                 'note':     f'Driving toward {seg_to}',
#                 'segment_to': seg_to,
#             })

#             miles_driven     += chunk_miles
#             miles_since_fuel += chunk_miles

#             # Fuel stop if we hit 1000 miles and haven't finished the segment
#             if miles_since_fuel >= FUEL_INTERVAL_MILES and not is_final_chunk:
#                 schedule_events.append({
#                     'type':     'on_duty',
#                     'duration': FUEL_STOP_DURATION,
#                     'location': seg_from,
#                     'note':     'Fuel stop',
#                 })
#                 miles_since_fuel = 0.0

#         # After arriving at pickup (end of segment 0): 1hr pickup on-duty
#         if seg_idx == 0:
#             schedule_events.append({
#                 'type':     'on_duty',
#                 'duration': PICKUP_DURATION,
#                 'location': pickup_location,
#                 'note':     'Pickup / Pre-trip inspection at pickup',
#             })

#     # Dropoff at the very end
#     schedule_events.append({
#         'type':     'on_duty',
#         'duration': DROPOFF_DURATION,
#         'location': dropoff_location,
#         'note':     'Dropoff / Post-trip inspection',
#     })

#     # --------------------------------------------------------
#     # Step 2: Simulate day-by-day with full HOS enforcement
#     # --------------------------------------------------------
#     days                = []
#     current_hour        = 0.0   # absolute trip time (hour 0 = trip start)
#     cycle_used          = float(current_cycle_used)
#     driving_since_break = 0.0   # cumulative driving since last 30-min break
#     window_start        = 0.0   # start of current 14-hr window
#     driving_in_window   = 0.0   # driving hours used in current window
#     total_miles_driven  = 0.0   # for per-day miles tracking

#     current_day_periods = []
#     current_day_remarks = []
#     current_day_num     = 1
#     current_day_miles   = 0.0
#     last_status         = None  # track previous status for remarks deduplication

#     def get_day_num(hour):
#         return int(hour // 24) + 1

#     def get_hour_in_day(hour):
#         return hour % 24

#     def flush_day(day_num, periods, remarks, day_miles):
#         """Finalize a calendar day — fill remainder with off_duty."""
#         totals = {'off_duty': 0.0, 'sleeper_berth': 0.0,
#                   'driving': 0.0, 'on_duty_not_driving': 0.0}

#         for p in periods:
#             dur = p['end_hour'] - p['start_hour']
#             totals[p['status']] = totals.get(p['status'], 0) + dur

#         total_accounted = sum(p['end_hour'] - p['start_hour'] for p in periods)
#         if total_accounted < 24.0 - 0.001:
#             remaining = 24.0 - total_accounted
#             last_end  = periods[-1]['end_hour'] if periods else 0.0
#             periods.append({
#                 'status':     'off_duty',
#                 'start_hour': round(last_end, 4),
#                 'end_hour':   round(last_end + remaining, 4),
#                 'location':   '',
#                 'note':       'Off duty',
#             })
#             totals['off_duty'] += remaining

#         days.append({
#             'day_num':      day_num,
#             'date_label':   f'Day {day_num}',
#             'duty_periods': periods,
#             'remarks':      remarks,
#             'totals':       {k: round(v, 2) for k, v in totals.items()},
#             'miles_today':  round(day_miles, 1),
#         })

#     def add_period(status, start, end, location, note):
#         """Add a duty period, splitting across midnight boundaries as needed."""
#         nonlocal current_day_periods, current_day_remarks, current_day_num
#         nonlocal current_day_miles, last_status

#         while start < end - 0.0001:
#             day_boundary = get_day_num(start) * 24.0
#             chunk_end    = min(end, day_boundary)
#             day_num      = get_day_num(start)

#             # Cross into new calendar day → flush the previous day
#             if day_num > current_day_num:
#                 flush_day(current_day_num, current_day_periods,
#                           current_day_remarks, current_day_miles)
#                 current_day_num     = day_num
#                 current_day_periods = []
#                 current_day_remarks = []
#                 current_day_miles   = 0.0
#                 last_status         = None  # reset for new day

#             start_in_day = get_hour_in_day(start)
#             end_in_day   = get_hour_in_day(chunk_end) if chunk_end % 24 != 0 else 24.0

#             current_day_periods.append({
#                 'status':     status,
#                 'start_hour': round(start_in_day, 4),
#                 'end_hour':   round(end_in_day, 4),
#                 'location':   location,
#                 'note':       note,
#             })

#             # Only add remark on STATUS CHANGE (FMCSA requirement)
#             if location and status != last_status:
#                 current_day_remarks.append({
#                     'hour':     round(start_in_day, 4),
#                     'location': location,
#                     'note':     note,
#                     'status':   status,
#                 })
#                 last_status = status

#             start = chunk_end

#     # --------------------------------------------------------
#     # Pre-trip inspection at current location (30 min on-duty)
#     # --------------------------------------------------------
#     add_period('on_duty_not_driving', 0.0, 0.5,
#                current_location, 'Pre-trip inspection')
#     current_hour  = 0.5
#     window_start  = 0.0
#     cycle_used   += 0.5

#     # --------------------------------------------------------
#     # Process each event with full HOS enforcement
#     # --------------------------------------------------------
#     for event in schedule_events:
#         duration = event['duration']
#         location = event.get('location', '')
#         note     = event.get('note', '')
#         etype    = event['type']

#         if etype == 'drive':
#             event_miles = event.get('miles', 0.0)
#             remaining   = duration
#             # Miles are proportional — track across sub-chunks
#             miles_left  = event_miles

#             while remaining > 0.0001:

#                 # --- Check: need 30-min break? ---
#                 if driving_since_break >= BREAK_AFTER_HOURS - 0.0001:
#                     add_period('off_duty', current_hour,
#                                current_hour + BREAK_DURATION, location,
#                                '30-min rest break (8-hr driving rule)')
#                     current_hour        += BREAK_DURATION
#                     driving_since_break  = 0.0
#                     cycle_used          += BREAK_DURATION

#                 # --- Check: 14-hr window exhausted? ---
#                 window_used = current_hour - window_start
#                 if window_used >= MAX_WINDOW_HOURS - 0.0001:
#                     add_period('sleeper_berth', current_hour,
#                                current_hour + MIN_REST_HOURS, location,
#                                '10-hr mandatory rest (14-hr window)')
#                     current_hour        += MIN_REST_HOURS
#                     window_start         = current_hour
#                     driving_in_window    = 0.0
#                     driving_since_break  = 0.0

#                 # --- Check: 11-hr driving limit reached? ---
#                 if driving_in_window >= MAX_DRIVING_HOURS - 0.0001:
#                     add_period('sleeper_berth', current_hour,
#                                current_hour + MIN_REST_HOURS, location,
#                                '10-hr mandatory rest (11-hr driving limit)')
#                     current_hour        += MIN_REST_HOURS
#                     window_start         = current_hour
#                     driving_in_window    = 0.0
#                     driving_since_break  = 0.0

#                 # --- Check: 70-hr cycle limit? ---
#                 if cycle_used >= MAX_CYCLE_HOURS - 0.0001:
#                     add_period('off_duty', current_hour,
#                                current_hour + 34.0, location,
#                                '34-hr restart (70-hr cycle limit)')
#                     current_hour        += 34.0
#                     cycle_used           = 0.0
#                     window_start         = current_hour
#                     driving_in_window    = 0.0
#                     driving_since_break  = 0.0

#                 # --- Calculate how much we can drive right now ---
#                 window_avail  = MAX_WINDOW_HOURS  - (current_hour - window_start)
#                 drive_avail   = MAX_DRIVING_HOURS - driving_in_window
#                 break_avail   = BREAK_AFTER_HOURS - driving_since_break
#                 cycle_avail   = MAX_CYCLE_HOURS   - cycle_used

#                 can_drive = min(remaining, window_avail, drive_avail,
#                                 break_avail, cycle_avail)
#                 can_drive = max(0.0, can_drive)

#                 if can_drive < 0.0001:
#                     continue  # loop back to enforce rest

#                 # Miles for this sub-chunk
#                 miles_this_chunk = (can_drive / duration) * event_miles if duration > 0 else 0.0
#                 miles_this_chunk = min(miles_this_chunk, miles_left)

#                 add_period('driving', current_hour,
#                            current_hour + can_drive, location, note)

#                 current_hour        += can_drive
#                 remaining           -= can_drive
#                 driving_since_break += can_drive
#                 driving_in_window   += can_drive
#                 cycle_used          += can_drive
#                 current_day_miles   += miles_this_chunk
#                 miles_left          -= miles_this_chunk
#                 total_miles_driven  += miles_this_chunk

#         elif etype == 'on_duty':
#             # Check 14-hr window before on-duty work
#             window_used = current_hour - window_start
#             if window_used >= MAX_WINDOW_HOURS - 0.0001:
#                 add_period('sleeper_berth', current_hour,
#                            current_hour + MIN_REST_HOURS, location,
#                            '10-hr mandatory rest')
#                 current_hour        += MIN_REST_HOURS
#                 window_start         = current_hour
#                 driving_in_window    = 0.0
#                 driving_since_break  = 0.0

#             add_period('on_duty_not_driving', current_hour,
#                        current_hour + duration, location, note)
#             current_hour += duration
#             cycle_used   += duration

#     # --------------------------------------------------------
#     # End-of-trip rest
#     # --------------------------------------------------------
#     add_period('sleeper_berth', current_hour,
#                current_hour + MIN_REST_HOURS,
#                dropoff_location, 'End of trip — rest')
#     current_hour += MIN_REST_HOURS

#     # Flush the final day
#     flush_day(current_day_num, current_day_periods,
#               current_day_remarks, current_day_miles)

#     return days


# def calculate_total_trip_miles(route_segments):
#     return round(sum(s['distance_miles'] for s in route_segments), 1)


# def calculate_total_driving_hours(days):
#     return round(sum(d['totals']['driving'] for d in days), 2)














from datetime import datetime, timedelta

# ============================================================
# FMCSA HOS Constants — 70hr/8-day Property Carrier Rule
# Source: FMCSA Interstate Truck Driver's Guide to Hours of Service (April 2022)
# ============================================================
MAX_DRIVING_HOURS   = 11.0   # § 395.3(a)(3) — max driving per shift
MAX_WINDOW_HOURS    = 14.0   # § 395.3(a)(2) — 14-hour driving window
MIN_REST_HOURS      = 10.0   # § 395.3(a)(1) — min consecutive off-duty
MAX_CYCLE_HOURS     = 70.0   # § 395.3(b)    — 70hr/8-day limit
BREAK_AFTER_HOURS   = 8.0    # § 395.3(a)(3)(ii) — 30-min break after 8 cumulative hrs
BREAK_DURATION      = 0.5    # 30 minutes
FUEL_INTERVAL_MILES = 1000.0 # Fuel stop every ≤1000 miles
PICKUP_DURATION     = 1.0    # 1 hour on-duty not driving for pickup
DROPOFF_DURATION    = 1.0    # 1 hour on-duty not driving for dropoff
FUEL_STOP_DURATION  = 0.5    # 30 minutes for fueling


def calculate_trip_schedule(current_location, pickup_location, dropoff_location,
                             current_cycle_used, route_segments):
    """
    Calculate a fully FMCSA-compliant HOS trip schedule.

    route_segments: [
        {'from': 'Chicago, IL', 'to': 'Dallas, TX', 'distance_miles': 925, 'duration_hours': 16.8},
        {'from': 'Dallas, TX',  'to': 'Los Angeles, CA', 'distance_miles': 1423, 'duration_hours': 25.9},
    ]

    Returns list of day objects:
        day = {
            'day_num': int,
            'date_label': str,
            'duty_periods': [{status, start_hour, end_hour, location, note}],
            'remarks': [{hour, location, note}],        # only status changes
            'totals': {off_duty, sleeper_berth, driving, on_duty_not_driving},
            'miles_today': float,
        }
    """

    # --------------------------------------------------------
    # Step 1: Build flat event list in CORRECT order:
    #   pre-trip → drive(current→pickup) → pickup → drive(pickup→dropoff) → dropoff
    # --------------------------------------------------------
    schedule_events = []

    for seg_idx, segment in enumerate(route_segments):
        seg_miles   = segment['distance_miles']
        seg_hours   = segment['duration_hours']
        seg_from    = segment['from']
        seg_to      = segment['to']

        # Split segment into drive chunks with fuel stops
        miles_driven   = 0.0
        miles_since_fuel = 0.0

        while miles_driven < seg_miles:
            miles_to_fuel    = FUEL_INTERVAL_MILES - miles_since_fuel
            miles_remaining  = seg_miles - miles_driven
            chunk_miles      = min(miles_to_fuel, miles_remaining)
            chunk_hours      = (chunk_miles / seg_miles) * seg_hours
            is_final_chunk   = (miles_driven + chunk_miles >= seg_miles - 0.01)

            # Location label: always the destination of this segment
            # Non-final chunks are en-route, final chunk has arrived
            drive_location = seg_to

            schedule_events.append({
                'type':     'drive',
                'duration': chunk_hours,
                'miles':    chunk_miles,
                'location': drive_location,
                'note':     f'Driving toward {seg_to}',
                'segment_to': seg_to,
            })

            miles_driven     += chunk_miles
            miles_since_fuel += chunk_miles

            # Fuel stop if we hit 1000 miles and haven't finished the segment
            if miles_since_fuel >= FUEL_INTERVAL_MILES and not is_final_chunk:
                schedule_events.append({
                    'type':     'on_duty',
                    'duration': FUEL_STOP_DURATION,
                    'location': f'En route to {seg_to}',
                    'note':     'Fuel stop',
                })
                miles_since_fuel = 0.0

        # After arriving at pickup (end of segment 0): 1hr pickup on-duty
        if seg_idx == 0:
            schedule_events.append({
                'type':     'on_duty',
                'duration': PICKUP_DURATION,
                'location': pickup_location,
                'note':     'Pickup / Pre-trip inspection at pickup',
            })

    # Dropoff at the very end
    schedule_events.append({
        'type':     'on_duty',
        'duration': DROPOFF_DURATION,
        'location': dropoff_location,
        'note':     'Dropoff / Post-trip inspection',
    })

    # --------------------------------------------------------
    # Step 2: Simulate day-by-day with full HOS enforcement
    # --------------------------------------------------------
    days                = []
    current_hour        = 0.0   # absolute trip time (hour 0 = trip start)
    cycle_used          = float(current_cycle_used)
    driving_since_break = 0.0   # cumulative driving since last 30-min break
    window_start        = 0.0   # start of current 14-hr window
    driving_in_window   = 0.0   # driving hours used in current window
    total_miles_driven  = 0.0   # for per-day miles tracking

    current_day_periods = []
    current_day_remarks = []
    current_day_num     = 1
    current_day_miles   = 0.0
    last_status         = None  # track previous status for remarks deduplication

    def get_day_num(hour):
        return int(hour // 24) + 1

    def get_hour_in_day(hour):
        return hour % 24

    def flush_day(day_num, periods, remarks, day_miles):
        """Finalize a calendar day — fill remainder with off_duty."""
        totals = {'off_duty': 0.0, 'sleeper_berth': 0.0,
                  'driving': 0.0, 'on_duty_not_driving': 0.0}

        for p in periods:
            dur = p['end_hour'] - p['start_hour']
            totals[p['status']] = totals.get(p['status'], 0) + dur

        total_accounted = sum(p['end_hour'] - p['start_hour'] for p in periods)
        if total_accounted < 24.0 - 0.001:
            remaining = 24.0 - total_accounted
            last_end  = periods[-1]['end_hour'] if periods else 0.0
            periods.append({
                'status':     'off_duty',
                'start_hour': round(last_end, 4),
                'end_hour':   round(last_end + remaining, 4),
                'location':   '',
                'note':       'Off duty',
            })
            totals['off_duty'] += remaining

        days.append({
            'day_num':      day_num,
            'date_label':   f'Day {day_num}',
            'duty_periods': periods,
            'remarks':      remarks,
            'totals':       {k: round(v, 2) for k, v in totals.items()},
            'miles_today':  round(day_miles, 1),
        })

    def add_period(status, start, end, location, note):
        """Add a duty period, splitting across midnight boundaries as needed."""
        nonlocal current_day_periods, current_day_remarks, current_day_num
        nonlocal current_day_miles, last_status

        while start < end - 0.0001:
            day_boundary = get_day_num(start) * 24.0
            chunk_end    = min(end, day_boundary)
            day_num      = get_day_num(start)

            # Cross into new calendar day → flush the previous day
            if day_num > current_day_num:
                flush_day(current_day_num, current_day_periods,
                          current_day_remarks, current_day_miles)
                current_day_num     = day_num
                current_day_periods = []
                current_day_remarks = []
                current_day_miles   = 0.0
                last_status         = None  # reset for new day

            start_in_day = get_hour_in_day(start)
            end_in_day   = get_hour_in_day(chunk_end) if chunk_end % 24 != 0 else 24.0

            current_day_periods.append({
                'status':     status,
                'start_hour': round(start_in_day, 4),
                'end_hour':   round(end_in_day, 4),
                'location':   location,
                'note':       note,
            })

            # Only add remark on STATUS CHANGE (FMCSA requirement)
            if location and status != last_status:
                current_day_remarks.append({
                    'hour':     round(start_in_day, 4),
                    'location': location,
                    'note':     note,
                    'status':   status,
                })
                last_status = status

            start = chunk_end

    # --------------------------------------------------------
    # Pre-trip inspection at current location (30 min on-duty)
    # --------------------------------------------------------
    add_period('on_duty_not_driving', 0.0, 0.5,
               current_location, 'Pre-trip inspection')
    current_hour  = 0.5
    window_start  = 0.0
    cycle_used   += 0.5

    # --------------------------------------------------------
    # Process each event with full HOS enforcement
    # --------------------------------------------------------
    for event in schedule_events:
        duration = event['duration']
        location = event.get('location', '')
        note     = event.get('note', '')
        etype    = event['type']

        if etype == 'drive':
            event_miles = event.get('miles', 0.0)
            remaining   = duration
            # Miles are proportional — track across sub-chunks
            miles_left  = event_miles

            while remaining > 0.0001:

                # --- Check: need 30-min break? ---
                if driving_since_break >= BREAK_AFTER_HOURS - 0.0001:
                    add_period('off_duty', current_hour,
                               current_hour + BREAK_DURATION, location,
                               '30-min rest break (8-hr driving rule)')
                    current_hour        += BREAK_DURATION
                    driving_since_break  = 0.0
                    cycle_used          += BREAK_DURATION

                # --- Check: 14-hr window exhausted? ---
                window_used = current_hour - window_start
                if window_used >= MAX_WINDOW_HOURS - 0.0001:
                    add_period('sleeper_berth', current_hour,
                               current_hour + MIN_REST_HOURS, location,
                               '10-hr mandatory rest (14-hr window)')
                    current_hour        += MIN_REST_HOURS
                    window_start         = current_hour
                    driving_in_window    = 0.0
                    driving_since_break  = 0.0

                # --- Check: 11-hr driving limit reached? ---
                if driving_in_window >= MAX_DRIVING_HOURS - 0.0001:
                    add_period('sleeper_berth', current_hour,
                               current_hour + MIN_REST_HOURS, location,
                               '10-hr mandatory rest (11-hr driving limit)')
                    current_hour        += MIN_REST_HOURS
                    window_start         = current_hour
                    driving_in_window    = 0.0
                    driving_since_break  = 0.0

                # --- Check: 70-hr cycle limit? ---
                if cycle_used >= MAX_CYCLE_HOURS - 0.0001:
                    add_period('off_duty', current_hour,
                               current_hour + 34.0, location,
                               '34-hr restart (70-hr cycle limit)')
                    current_hour        += 34.0
                    cycle_used           = 0.0
                    window_start         = current_hour
                    driving_in_window    = 0.0
                    driving_since_break  = 0.0

                # --- Calculate how much we can drive right now ---
                window_avail  = MAX_WINDOW_HOURS  - (current_hour - window_start)
                drive_avail   = MAX_DRIVING_HOURS - driving_in_window
                break_avail   = BREAK_AFTER_HOURS - driving_since_break
                cycle_avail   = MAX_CYCLE_HOURS   - cycle_used

                can_drive = min(remaining, window_avail, drive_avail,
                                break_avail, cycle_avail)
                can_drive = max(0.0, can_drive)

                if can_drive < 0.0001:
                    continue  # loop back to enforce rest

                # Miles for this sub-chunk
                miles_this_chunk = (can_drive / duration) * event_miles if duration > 0 else 0.0
                miles_this_chunk = min(miles_this_chunk, miles_left)

                add_period('driving', current_hour,
                           current_hour + can_drive, location, note)

                current_hour        += can_drive
                remaining           -= can_drive
                driving_since_break += can_drive
                driving_in_window   += can_drive
                cycle_used          += can_drive
                current_day_miles   += miles_this_chunk
                miles_left          -= miles_this_chunk
                total_miles_driven  += miles_this_chunk

        elif etype == 'on_duty':
            # Check 14-hr window before on-duty work
            window_used = current_hour - window_start
            if window_used >= MAX_WINDOW_HOURS - 0.0001:
                add_period('sleeper_berth', current_hour,
                           current_hour + MIN_REST_HOURS, location,
                           '10-hr mandatory rest')
                current_hour        += MIN_REST_HOURS
                window_start         = current_hour
                driving_in_window    = 0.0
                driving_since_break  = 0.0

            add_period('on_duty_not_driving', current_hour,
                       current_hour + duration, location, note)
            current_hour += duration
            cycle_used   += duration

    # --------------------------------------------------------
    # End-of-trip rest
    # --------------------------------------------------------
    add_period('sleeper_berth', current_hour,
               current_hour + MIN_REST_HOURS,
               dropoff_location, 'End of trip — rest')
    current_hour += MIN_REST_HOURS

    # Flush the final day
    flush_day(current_day_num, current_day_periods,
              current_day_remarks, current_day_miles)

    return days


def calculate_total_trip_miles(route_segments):
    return round(sum(s['distance_miles'] for s in route_segments), 1)


def calculate_total_driving_hours(days):
    return round(sum(d['totals']['driving'] for d in days), 2)
