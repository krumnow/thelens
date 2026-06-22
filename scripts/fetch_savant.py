#!/usr/bin/env python3
"""
fetch_savant.py — Baseball Savant data fetcher for The Lens
Runs daily via GitHub Actions, writes JSON files to data/

SB-specific additions (Path B):
  - savant-pop-time.json      : catcher pop times (exchange + transfer + throw)
  - savant-pitch-tempo.json   : pitcher pace/tempo (time to plate)
  - savant-baserunning.json   : runner extra base taking %, attempt rates
  - savant-sb-leaders.json    : full SB leaderboard with Statcast context
"""

import csv
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from io import StringIO

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)

SEASON = datetime.now().year
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; TheLens/1.0)',
    'Accept':     'text/csv,application/json,*/*',
}

def fetch_url(url, retries=3, delay=4):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode('utf-8')
        except urllib.error.HTTPError as e:
            print(f'  HTTP {e.code} on attempt {attempt+1}: {url[:80]}')
        except Exception as e:
            print(f'  Error on attempt {attempt+1}: {e}')
        if attempt < retries - 1:
            time.sleep(delay)
    return None

def parse_csv(text):
    if not text or not text.strip():
        return []
    reader = csv.DictReader(StringIO(text))
    return list(reader)

def safe_float(val, default=None):
    try:
        return float(val) if val not in (None, '', 'null') else default
    except (ValueError, TypeError):
        return default

def safe_int(val, default=None):
    try:
        return int(val) if val not in (None, '', 'null') else default
    except (ValueError, TypeError):
        return default

def write_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    size = os.path.getsize(path)
    n = len(data) if isinstance(data, dict) else len(data) if isinstance(data, list) else '?'
    print(f'  Wrote {filename} ({size/1024:.1f} KB, {n} entries)')

# ════════════════════════════════════
# EXISTING FETCHERS
# ════════════════════════════════════

def fetch_pitcher_arsenal():
    print('\n[1/11] Pitcher arsenal...')
    url = f'https://baseballsavant.mlb.com/leaderboard/pitch-arsenal-stats?type=pitcher&pitchType=&year={SEASON}&team=&min=25&csv=true'
    text = fetch_url(url)
    if not text:
        print('  Arsenal fetch failed')
        return {}
    rows = parse_csv(text)
    result = {}
    for row in rows:
        pid = safe_int(row.get('pitcher_id') or row.get('player_id'))
        if not pid:
            continue
        if pid not in result:
            result[pid] = {'pitches': []}
        result[pid]['pitches'].append({
            'pitch_type': row.get('pitch_type', ''),
            'pitch_name': row.get('pitch_name', ''),
            'run_value':  safe_float(row.get('run_value_per100') or row.get('run_value')),
            'pa':         safe_int(row.get('pa')),
            'usage_pct':  safe_float(row.get('pitch_usage') or row.get('pitch_percent')),
            'avg_speed':  safe_float(row.get('avg_speed') or row.get('release_speed')),
            'avg_spin':   safe_float(row.get('avg_spin')),
            'whiff_pct':  safe_float(row.get('whiff_percent')),
            'k_pct':      safe_float(row.get('k_percent')),
            'put_away':   safe_float(row.get('put_away')),
        })
    print(f'  {len(result)} pitchers')
    return result

def fetch_pitcher_expected():
    print('\n[2/11] Pitcher expected stats...')
    url = f'https://baseballsavant.mlb.com/leaderboard/expected_statistics?type=pitcher&year={SEASON}&position=&team=&min=25&csv=true'
    text = fetch_url(url)
    if not text:
        return {}
    rows = parse_csv(text)
    result = {}
    for row in rows:
        pid = safe_int(row.get('player_id'))
        if not pid:
            continue
        result[pid] = {
            'player_name':  row.get('player_name', ''),
            'xba':          safe_float(row.get('xba')),
            'xslg':         safe_float(row.get('xslg')),
            'xwoba':        safe_float(row.get('xwoba')),
            'xera':         safe_float(row.get('xera')),
            'xfip':         safe_float(row.get('xfip') or row.get('xfip-')),
            'barrel_pct':   safe_float(row.get('barrel_batted_rate') or row.get('barrel_pct')),
            'hard_hit_pct': safe_float(row.get('hard_hit_percent') or row.get('hard_hit_pct')),
            'exit_velo_avg':safe_float(row.get('avg_exit_velocity') or row.get('exit_velocity_avg')),
            'k_pct':        safe_float(row.get('k_percent')),
            'bb_pct':       safe_float(row.get('bb_percent')),
            'woba':         safe_float(row.get('woba')),
            'pa':           safe_int(row.get('pa')),
        }
    print(f'  {len(result)} pitchers')
    return result

def fetch_pitcher_percentiles():
    print('\n[3/11] Pitcher percentiles...')
    url = f'https://baseballsavant.mlb.com/leaderboard/percentile-rankings?type=pit&year={SEASON}&position=&team=&csv=true'
    text = fetch_url(url)
    if not text:
        return {}
    rows = parse_csv(text)
    result = {}
    SKIP = {'player_name','player_id','year','team_name_abbrev','position','pa'}
    for row in rows:
        pid = safe_int(row.get('player_id'))
        if not pid:
            continue
        percentiles = {k: safe_float(v) for k, v in row.items() if k not in SKIP and safe_float(v) is not None}
        result[pid] = {'player_name': row.get('player_name', ''), 'percentiles': percentiles}
    print(f'  {len(result)} pitchers')
    return result

def fetch_hitter_expected():
    print('\n[4/11] Hitter expected stats...')
    url = f'https://baseballsavant.mlb.com/leaderboard/expected_statistics?type=batter&year={SEASON}&position=&team=&min=25&csv=true'
    text = fetch_url(url)
    if not text:
        return {}
    rows = parse_csv(text)
    result = {}
    for row in rows:
        pid = safe_int(row.get('player_id'))
        if not pid:
            continue
        result[pid] = {
            'player_name':   row.get('player_name', ''),
            'xba':           safe_float(row.get('xba')),
            'xslg':          safe_float(row.get('xslg')),
            'xwoba':         safe_float(row.get('xwoba')),
            'barrel_pct':    safe_float(row.get('barrel_batted_rate') or row.get('barrel_pct')),
            'hard_hit_pct':  safe_float(row.get('hard_hit_percent') or row.get('hard_hit_pct')),
            'exit_velo_avg': safe_float(row.get('avg_exit_velocity') or row.get('exit_velocity_avg')),
            'k_pct':         safe_float(row.get('k_percent')),
            'bb_pct':        safe_float(row.get('bb_percent')),
            'woba':          safe_float(row.get('woba')),
            'pa':            safe_int(row.get('pa')),
        }
    print(f'  {len(result)} hitters')
    return result

def fetch_hitter_statcast():
    print('\n[5/11] Hitter statcast / discipline...')
    sprint_url     = f'https://baseballsavant.mlb.com/leaderboard/sprint_speed?year={SEASON}&position=&team=&min=10&csv=true'
    discipline_url = f'https://baseballsavant.mlb.com/leaderboard/plate-discipline?year={SEASON}&position=&team=&min=25&csv=true'
    result = {}
    for url, label in [(sprint_url, 'sprint'), (discipline_url, 'discipline')]:
        text = fetch_url(url)
        if not text:
            continue
        rows = parse_csv(text)
        for row in rows:
            pid = safe_int(row.get('player_id'))
            if not pid:
                continue
            if pid not in result:
                result[pid] = {}
            if label == 'sprint':
                result[pid]['sprint_speed'] = safe_float(row.get('sprint_speed') or row.get('hp_to_1b'))
                result[pid]['player_name']  = row.get('player_name') or result[pid].get('player_name','')
            else:
                result[pid].update({
                    'chase_pct':          safe_float(row.get('o_swing_percent') or row.get('chase_percent')),
                    'whiff_pct':          safe_float(row.get('whiff_percent') or row.get('swstr_percent')),
                    'zone_swing':         safe_float(row.get('z_swing_percent')),
                    'zone_contact':       safe_float(row.get('z_contact_percent')),
                    'first_pitch_swing':  safe_float(row.get('f_strike_percent')),
                    'swing_pct':          safe_float(row.get('swing_percent')),
                    'contact_pct':        safe_float(row.get('contact_percent')),
                    'gb_pct':             safe_float(row.get('gb_percent')),
                    'fb_pct':             safe_float(row.get('fb_percent')),
                    'ld_pct':             safe_float(row.get('ld_percent')),
                })
        print(f'  {label}: {len(result)} players')
    return result

def fetch_hitter_percentiles():
    print('\n[6/11] Hitter percentiles...')
    url = f'https://baseballsavant.mlb.com/leaderboard/percentile-rankings?type=bat&year={SEASON}&position=&team=&csv=true'
    text = fetch_url(url)
    if not text:
        return {}
    rows = parse_csv(text)
    result = {}
    SKIP = {'player_name','player_id','year','team_name_abbrev','position','pa'}
    for row in rows:
        pid = safe_int(row.get('player_id'))
        if not pid:
            continue
        percentiles = {k: safe_float(v) for k, v in row.items() if k not in SKIP and safe_float(v) is not None}
        result[pid] = {'player_name': row.get('player_name', ''), 'percentiles': percentiles}
    print(f'  {len(result)} hitters')
    return result

# ════════════════════════════════════
# NEW SB-SPECIFIC FETCHERS (PATH B)
# ════════════════════════════════════

def fetch_pop_time():
    """
    Catcher pop time — the single most important SB factor we can add.
    pop_time = exchange_time + throw_time (2.0s elite, 2.1s avg, 2.2s+ weak)
    Savant publishes this on their catcher framing/blocking leaderboard.
    """
    print('\n[7/11] Catcher pop time...')
    url = f'https://baseballsavant.mlb.com/leaderboard/poptime?year={SEASON}&team=&min2b=5&min3b=0&csv=true'
    text = fetch_url(url)
    if not text:
        print('  Pop time fetch failed')
        return {}
    rows = parse_csv(text)
    result = {}
    for row in rows:
        pid = safe_int(row.get('catcher_id') or row.get('player_id'))
        if not pid:
            continue
        result[pid] = {
            'player_name':    row.get('catcher_name') or row.get('player_name', ''),
            'team':           row.get('team_name', ''),
            # 2B pop time (most common steal target)
            'pop_2b':         safe_float(row.get('pop_2b_sba_avgpoptime') or row.get('avg_pop_time') or row.get('pop_time_2b')),
            # 3B pop time
            'pop_3b':         safe_float(row.get('pop_3b_sba_avgpoptime') or row.get('pop_time_3b')),
            # Exchange time (fielding the ball)
            'exchange_2b':    safe_float(row.get('exchange_2b_3b_sba') or row.get('exchange_time')),
            # Throw speed (mph)
            'throw_speed_2b': safe_float(row.get('maxeff_arm_2b_3b_sba') or row.get('throw_speed')),
            # Attempts caught
            'att_caught':     safe_int(row.get('cs') or row.get('caught_stealing')),
            'att_total':      safe_int(row.get('sba') or row.get('stolen_base_attempts')),
            # Caught stealing %
            'cs_pct':         safe_float(row.get('cs_pct') or row.get('cspct')),
        }
    print(f'  {len(result)} catchers with pop time')
    return result

def fetch_pitch_tempo():
    """
    Pitcher pace/tempo — time between pitches and time to plate.
    Faster to plate = harder to steal. Slow tempo = easier.
    """
    print('\n[8/11] Pitcher pitch tempo...')
    # Pace leaderboard — seconds between pitches, time to plate
    url = f'https://baseballsavant.mlb.com/leaderboard/pitching-alignment?year={SEASON}&team=&min=100&csv=true'
    text = fetch_url(url)

    # Fallback: statcast search for tempo data
    if not text:
        url2 = f'https://baseballsavant.mlb.com/leaderboard/outs_above_average?type=Pitcher&year={SEASON}&team=&min=100&pos=&outstatus=&csv=true'
        text = fetch_url(url2)

    if not text:
        print('  Pitch tempo fetch failed — trying pace leaderboard')
        # Try pace of game endpoint
        url3 = f'https://baseballsavant.mlb.com/leaderboard/pitch-tempo?year={SEASON}&team=&min=100&hand=&csv=true'
        text = fetch_url(url3)

    if not text:
        print('  All tempo endpoints failed')
        return {}

    rows = parse_csv(text)
    result = {}
    for row in rows:
        pid = safe_int(row.get('pitcher_id') or row.get('player_id'))
        if not pid:
            continue
        result[pid] = {
            'player_name': row.get('pitcher_name') or row.get('player_name', ''),
            'team':        row.get('team_name', ''),
            # Seconds from pitcher receiving ball to pitch release (with runner on)
            'pace_runner_on':  safe_float(row.get('pace_per_pitch_rascore') or row.get('pace_runner') or row.get('time_to_plate_runner') or row.get('tempo_runner')),
            # Seconds from pitcher receiving ball to pitch release (no runner)
            'pace_empty':      safe_float(row.get('pace_per_pitch') or row.get('pace_empty') or row.get('tempo_empty')),
            # Pickoff attempts per runner
            'pickoff_attempts':safe_int(row.get('pickoff_attempts') or row.get('pickoffs')),
            # Balk rate
            'balks':           safe_int(row.get('balks')),
        }
    print(f'  {len(result)} pitchers with tempo data')
    return result

def fetch_baserunning():
    """
    Baserunning aggression stats — extra base taking %, attempt rates, OAA.
    """
    print('\n[9/11] Baserunning stats...')
    url = f'https://baseballsavant.mlb.com/leaderboard/baserunning?year={SEASON}&team=&min=10&csv=true'
    text = fetch_url(url)
    if not text:
        print('  Baserunning fetch failed')
        return {}
    rows = parse_csv(text)
    result = {}
    for row in rows:
        pid = safe_int(row.get('runner_id') or row.get('player_id'))
        if not pid:
            continue
        result[pid] = {
            'player_name':      row.get('runner_name') or row.get('player_name', ''),
            'team':             row.get('team_name', ''),
            # Extra base taking
            'xbt_pct':          safe_float(row.get('xbt_pct') or row.get('extra_base_taken_pct')),  # 1st->3rd, 2nd->home
            'xbt_opportunities':safe_int(row.get('xbt_opportunities')),
            'xbt_taken':        safe_int(row.get('xbt')),
            # Stolen base specific
            'sb':               safe_int(row.get('sb') or row.get('stolen_bases')),
            'cs':               safe_int(row.get('cs') or row.get('caught_stealing')),
            'sb_pct':           safe_float(row.get('sb_pct') or row.get('sb_success_pct')),
            'sb_opportunities': safe_int(row.get('sb_opportunities')),
            # Sprint speed (redundant but good to have here too)
            'sprint_speed':     safe_float(row.get('sprint_speed')),
            # OAA baserunning (overall value)
            'br_runs':          safe_float(row.get('br_runs_above_avg') or row.get('baserunning_runs')),
        }
    print(f'  {len(result)} runners with baserunning data')
    return result

def fetch_sb_leaders():
    """
    Full SB leaderboard with Statcast context.
    Combines SB leaders with sprint speed and pop time context.
    """
    print('\n[10/11] SB leaders with Statcast...')
    url = f'https://baseballsavant.mlb.com/leaderboard/sprint_speed?year={SEASON}&position=&team=&min=10&csv=true'
    text = fetch_url(url)
    if not text:
        print('  SB leaders fetch failed')
        return {}
    rows = parse_csv(text)
    # Filter to players with meaningful sprint speed (likely baserunners)
    result = {}
    for row in rows:
        pid = safe_int(row.get('player_id'))
        if not pid:
            continue
        speed = safe_float(row.get('sprint_speed') or row.get('hp_to_1b'))
        if not speed:
            continue
        result[pid] = {
            'player_name':   row.get('player_name', ''),
            'team':          row.get('team_name', '') or row.get('team', ''),
            'sprint_speed':  speed,
            'hp_to_1b':      safe_float(row.get('hp_to_1b')),
            'runs':          safe_int(row.get('runs')),
            'competitive_runs': safe_int(row.get('competitive_runs')),
            'percentile':    safe_float(row.get('speed_percentile') or row.get('percentile')),
        }
    print(f'  {len(result)} players with sprint speed data')
    return result

def fetch_pitcher_sb_metrics():
    """
    Pitcher-specific SB metrics from Statcast.
    Time to plate (extension), pickoff frequency.
    This uses the statcast search API for pitcher data.
    """
    print('\n[11/11] Pitcher SB metrics...')
    # Try the pitching tempo/pace endpoint specifically for SB context
    url = (
        f'https://baseballsavant.mlb.com/statcast_search/csv?all=true'
        f'&hfSea={SEASON}%7C&player_type=pitcher&hfGT=R%7C'
        f'&group_by=name&min_pitches=100&sort_col=pitches&sort_order=desc'
        f'&chk_stats_n_thru_order=on&type=details'
        f'&pitchers_lookup%5B%5D=&hfFlag=is%3B' # with runners on
    )

    # Simpler: use the existing arsenal endpoint and note fast/slow tempo pitchers
    # We'll derive tempo proxy from pitch type mix:
    # High FB% pitchers tend to be faster to plate
    # High offspeed% pitchers tend to be slower (easier to steal)
    # Pull this from the arsenal data we already fetch

    # For now fetch the pitch tempo leaderboard which has time to plate
    url2 = f'https://baseballsavant.mlb.com/leaderboard/pitch-tempo?year={SEASON}&team=&min=100&hand=&csv=true'
    text = fetch_url(url2)

    if not text:
        print('  Pitcher SB metrics unavailable from this endpoint')
        return {}

    rows = parse_csv(text)
    result = {}
    for row in rows:
        pid = safe_int(row.get('pitcher_id') or row.get('player_id'))
        if not pid:
            continue
        result[pid] = {
            'player_name':        row.get('pitcher_name') or row.get('player_name', ''),
            'time_to_plate':      safe_float(row.get('time_to_plate') or row.get('avg_time_to_plate') or row.get('pitch_tempo')),
            'time_to_plate_bos':  safe_float(row.get('time_to_plate_bos')),  # bases occupied
            'extension':          safe_float(row.get('release_extension') or row.get('extension')),
            'pickoffs':           safe_int(row.get('pickoffs') or row.get('pickoff_attempts')),
        }
    print(f'  {len(result)} pitchers with SB tempo metrics')
    return result

# ════════════════════════════════════
# META
# ════════════════════════════════════

def write_meta(files_updated):
    meta = {
        'updated':       datetime.now(timezone.utc).isoformat(),
        'season':        SEASON,
        'files_updated': files_updated,
    }
    write_json('savant-meta.json', meta)

# ════════════════════════════════════
# MAIN
# ════════════════════════════════════

def main():
    print(f'=== Baseball Savant Fetch — {SEASON} season ===')
    print(f'Output directory: {os.path.abspath(DATA_DIR)}')

    files_updated = []
    errors = []

    tasks = [
        ('arsenal',          fetch_pitcher_arsenal,   'savant-arsenal.json'),
        ('pitcher-expected', fetch_pitcher_expected,  'savant-expected.json'),
        ('pitcher-pct',      fetch_pitcher_percentiles,'savant-percentiles.json'),
        ('hitter-expected',  fetch_hitter_expected,   'savant-hitter-expected.json'),
        ('hitter-statcast',  fetch_hitter_statcast,   'savant-hitter-statcast.json'),
        ('hitter-pct',       fetch_hitter_percentiles,'savant-hitter-percentiles.json'),
        # SB-specific
        ('pop-time',         fetch_pop_time,          'savant-pop-time.json'),
        ('pitch-tempo',      fetch_pitch_tempo,        'savant-pitch-tempo.json'),
        ('baserunning',      fetch_baserunning,        'savant-baserunning.json'),
        ('sb-leaders',       fetch_sb_leaders,         'savant-sb-leaders.json'),
        ('pitcher-sb',       fetch_pitcher_sb_metrics,'savant-pitcher-sb.json'),
    ]

    for key, fn, filename in tasks:
        try:
            data = fn()
            if data:
                write_json(filename, data)
                files_updated.append(filename)
            else:
                print(f'  {key}: no data returned (endpoint may be unavailable)')
        except Exception as e:
            print(f'  ERROR [{key}]: {e}')
            errors.append(key)

    write_meta(files_updated)
    files_updated.append('savant-meta.json')

    print(f'\n=== Done ===')
    print(f'Updated: {len(files_updated)} files')
    for f in files_updated:
        print(f'  ✓ {f}')
    if errors:
        print(f'\nPartial failures (non-critical): {", ".join(errors)}')
        # Don't exit(1) for SB-specific failures — core data still usable
        non_core_errors = [e for e in errors if e not in ('arsenal','pitcher-expected','hitter-expected','hitter-statcast')]
        if len(non_core_errors) == len(errors):
            print('Core data OK — SB endpoint failures are non-critical')
        else:
            sys.exit(1)
    else:
        print('All files updated successfully.')

if __name__ == '__main__':
    main()
