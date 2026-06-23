#!/usr/bin/env python3
"""
fetch_savant.py — Baseball Savant data fetcher for The Lens
Uses savant-extras + pybaseball for verified working endpoints.
"""

import json, os, sys, time
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(DATA_DIR, exist_ok=True)
SEASON = datetime.now().year

def write_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    print(f'  ✓ {filename} ({os.path.getsize(path)/1024:.1f} KB, {len(data)} entries)')

def safe(val, default=None):
    try:
        v = float(val)
        return None if v != v else v  # NaN check
    except:
        return default

def df_to_dict(df, key_col, fields):
    """Convert dataframe to {id: {field: val}} dict."""
    result = {}
    for _, row in df.iterrows():
        key = row.get(key_col)
        if key is None:
            continue
        try:
            key = int(key)
        except:
            continue
        result[key] = {f: safe(row.get(f)) for f in fields if row.get(f) is not None}
    return result

def main():
    print(f'=== Baseball Savant Fetch — {SEASON} ===')

    # Install dependencies
    os.system('pip install savant-extras pybaseball --quiet')

    import pybaseball as pb
    pb.cache.enable()

    files_updated = []
    errors = []

    # ── 1. PITCHER ARSENAL ──
    try:
        print('\n[1/11] Pitcher arsenal...')
        df = pb.statcast_pitcher_arsenal_stats(SEASON, min_pa=25)
        result = {}
        for _, row in df.iterrows():
            pid = int(row.get('pitcher_id', 0) or 0)
            if not pid: continue
            if pid not in result: result[pid] = {'pitches': []}
            result[pid]['pitches'].append({
                'pitch_type': row.get('pitch_type'),
                'pitch_name': row.get('pitch_name'),
                'usage_pct':  safe(row.get('pitch_usage') or row.get('pitch_percent')),
                'avg_speed':  safe(row.get('avg_speed')),
                'whiff_pct':  safe(row.get('whiff_percent')),
                'k_pct':      safe(row.get('k_percent')),
                'run_value':  safe(row.get('run_value_per100')),
            })
        write_json('savant-arsenal.json', result)
        files_updated.append('savant-arsenal.json')
    except Exception as e:
        print(f'  arsenal error: {e}'); errors.append('arsenal')

    # ── 2. PITCHER EXPECTED ──
    try:
        print('\n[2/11] Pitcher expected stats...')
        df = pb.statcast_pitcher_expected_stats(SEASON, minPA=25)
        result = {}
        for _, row in df.iterrows():
            pid = int(row.get('player_id', 0) or 0)
            if not pid: continue
            result[pid] = {
                'player_name': row.get('last_name, first_name') or row.get('player_name',''),
                'xera':  safe(row.get('xera')),
                'xba':   safe(row.get('est_ba')),
                'xslg':  safe(row.get('est_slg')),
                'xwoba': safe(row.get('est_woba')),
                'k_pct': safe(row.get('k_percent')),
                'bb_pct':safe(row.get('bb_percent')),
                'barrel_pct':   safe(row.get('barrel_batted_rate')),
                'hard_hit_pct': safe(row.get('hard_hit_percent')),
                'exit_velo_avg':safe(row.get('avg_exit_velocity')),
            }
        write_json('savant-expected.json', result)
        files_updated.append('savant-expected.json')
    except Exception as e:
        print(f'  pitcher-expected error: {e}'); errors.append('pitcher-expected')

    # ── 3. PITCHER PERCENTILES ──
    try:
        print('\n[3/11] Pitcher percentiles...')
        df = pb.statcast_pitcher_percentile_ranks(SEASON)
        result = {}
        SKIP = {'player_name','player_id','year','team_name_abbrev','position','pa',
                'last_name, first_name'}
        for _, row in df.iterrows():
            pid = int(row.get('player_id', 0) or 0)
            if not pid: continue
            percentiles = {k: safe(v) for k, v in row.items()
                          if k not in SKIP and safe(v) is not None}
            result[pid] = {
                'player_name': row.get('last_name, first_name') or row.get('player_name',''),
                'percentiles': percentiles
            }
        write_json('savant-percentiles.json', result)
        files_updated.append('savant-percentiles.json')
    except Exception as e:
        print(f'  pitcher-pct error: {e}'); errors.append('pitcher-pct')

    # ── 4. HITTER EXPECTED ──
    try:
        print('\n[4/11] Hitter expected stats...')
        df = pb.statcast_batter_expected_stats(SEASON, minPA=25)
        result = {}
        for _, row in df.iterrows():
            pid = int(row.get('player_id', 0) or 0)
            if not pid: continue
            result[pid] = {
                'player_name':   row.get('last_name, first_name') or row.get('player_name',''),
                'xba':           safe(row.get('est_ba')),
                'xslg':          safe(row.get('est_slg')),
                'xwoba':         safe(row.get('est_woba')),
                'barrel_pct':    safe(row.get('barrel_batted_rate')),
                'hard_hit_pct':  safe(row.get('hard_hit_percent')),
                'exit_velo_avg': safe(row.get('avg_exit_velocity')),
                'k_pct':         safe(row.get('k_percent')),
                'bb_pct':        safe(row.get('bb_percent')),
            }
        write_json('savant-hitter-expected.json', result)
        files_updated.append('savant-hitter-expected.json')
    except Exception as e:
        print(f'  hitter-expected error: {e}'); errors.append('hitter-expected')

    # ── 5. SPRINT SPEED + DISCIPLINE ──
    try:
        print('\n[5/11] Sprint speed...')
        df = pb.statcast_sprint_speed(SEASON, min_opp=10)
        result = {}
        for _, row in df.iterrows():
            pid = int(row.get('player_id', 0) or 0)
            if not pid: continue
            result[pid] = {
                'player_name': row.get('player_name',''),
                'sprint_speed': safe(row.get('sprint_speed')),
                'hp_to_1b':     safe(row.get('hp_to_1b')),
                'percentile':   safe(row.get('speed_percentile')),
            }
        write_json('savant-hitter-statcast.json', result)
        write_json('savant-sb-leaders.json', result)
        files_updated += ['savant-hitter-statcast.json','savant-sb-leaders.json']
    except Exception as e:
        print(f'  sprint error: {e}'); errors.append('sprint')

    # ── 6. HITTER PERCENTILES ──
    try:
        print('\n[6/11] Hitter percentiles...')
        df = pb.statcast_batter_percentile_ranks(SEASON)
        result = {}
        SKIP = {'player_name','player_id','year','team_name_abbrev','position','pa',
                'last_name, first_name'}
        for _, row in df.iterrows():
            pid = int(row.get('player_id', 0) or 0)
            if not pid: continue
            percentiles = {k: safe(v) for k, v in row.items()
                          if k not in SKIP and safe(v) is not None}
            result[pid] = {
                'player_name': row.get('last_name, first_name') or row.get('player_name',''),
                'percentiles': percentiles
            }
        write_json('savant-hitter-percentiles.json', result)
        files_updated.append('savant-hitter-percentiles.json')
    except Exception as e:
        print(f'  hitter-pct error: {e}'); errors.append('hitter-pct')

    # ── 7. CATCHER POP TIME — direct Savant URL ──
    try:
        print('\n[7/11] Catcher pop time...')
        import urllib.request, csv as csvmod
        from io import StringIO

        result = {}
        hdrs = {'User-Agent': 'Mozilla/5.0 (compatible; TheLens/1.0)', 'Accept': 'text/csv,*/*'}

        # Direct Savant pop time leaderboard
        pop_url = f'https://baseballsavant.mlb.com/leaderboard/poptime?year={SEASON}&team=&min2b=5&min3b=0&csv=true'
        try:
            req = urllib.request.Request(pop_url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=30) as r:
                text = r.read().decode('utf-8')
            if text and len(text) > 200:
                reader = csvmod.DictReader(StringIO(text))
                rows = list(reader)
                print(f'  Got {len(rows)} rows, columns: {list(rows[0].keys()) if rows else []}')
                for row in rows:
                    pid = int(row.get('catcher_id') or row.get('player_id') or 0)
                    if not pid: continue
                    result[pid] = {
                        'player_name':    row.get('catcher_name') or row.get('player_name',''),
                        'team':           row.get('team_name','') or row.get('team',''),
                        'pop_2b':         safe(row.get('pop_2b_sba_avgpoptime') or row.get('avg_pop_2b_sba') or row.get('pop2b_avg') or row.get('pop_2b')),
                        'pop_3b':         safe(row.get('pop_3b_sba_avgpoptime') or row.get('avg_pop_3b_sba') or row.get('pop_3b')),
                        'exchange_2b':    safe(row.get('exchange_2b_3b_sba') or row.get('exchange_2b')),
                        'throw_speed_2b': safe(row.get('maxeff_arm_2b_3b_sba') or row.get('arm_strength_2b')),
                        'cs_pct':         safe(row.get('cs_pct') or row.get('caught_stealing_pct')),
                        'att_total':      safe(row.get('n_cs_att_2b_3b') or row.get('sba') or row.get('att_total')),
                    }
                print(f'  Direct URL: {len(result)} catchers')
                if result:
                    # Log sample to verify fields
                    sample_pid = list(result.keys())[0]
                    print(f'  Sample: {result[sample_pid]}')
        except Exception as e2:
            print(f'  Direct URL failed: {e2}')

        # Fallback: savant-extras
        if not result:
            try:
                from savant_extras import catcher_throwing
                df = catcher_throwing(SEASON)
                print(f'  savant-extras cols: {list(df.columns) if not df.empty else "empty"}')
                if not df.empty:
                    for _, row in df.iterrows():
                        pid = int(row.get('catcher_id') or row.get('player_id') or 0)
                        if not pid: continue
                        # Try every possible column name
                        pop = None
                        for col in ['pop_2b_sba_avgpoptime','avg_pop_2b_sba','pop2b_avg','pop_2b','avg_pop_time']:
                            v = safe(row.get(col))
                            if v is not None: pop = v; break
                        result[pid] = {
                            'player_name': row.get('catcher_name') or row.get('player_name',''),
                            'team': str(row.get('team_name','') or row.get('team','')),
                            'pop_2b': pop,
                            'cs_pct': safe(row.get('cs_pct') or row.get('caught_stealing_pct')),
                        }
                    print(f'  savant-extras: {len(result)} catchers')
            except Exception as e3:
                print(f'  savant-extras fallback: {e3}')

        if result:
            write_json('savant-pop-time.json', result)
            files_updated.append('savant-pop-time.json')
        else:
            print('  pop-time: no data from any source')
            errors.append('pop-time')
    except Exception as e:
        print(f'  pop-time error: {e}'); errors.append('pop-time')


    # ── 8. PITCH TEMPO — direct URL with savant-extras fallback ──
    try:
        print('\n[8/11] Pitch tempo...')
        import urllib.request, csv as csvmod
        from io import StringIO

        result = {}

        # Try direct Savant URL first
        direct_url = f'https://baseballsavant.mlb.com/leaderboard/pitch-tempo?year={SEASON}&team=&min=100&hand=&csv=true'
        hdrs = {'User-Agent': 'Mozilla/5.0 (compatible; TheLens/1.0)', 'Accept': 'text/csv,*/*'}
        try:
            req = urllib.request.Request(direct_url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=30) as r:
                text = r.read().decode('utf-8')
            if text and len(text) > 200:
                reader = csvmod.DictReader(StringIO(text))
                for row in reader:
                    pid = int(row.get('pitcher_id') or row.get('player_id') or 0)
                    if not pid: continue
                    result[pid] = {
                        'player_name':    row.get('pitcher_name') or row.get('player_name',''),
                        'team':           row.get('team_name',''),
                        'pace_runner_on': safe(row.get('pace_per_pitch_rascore') or row.get('pace_rascore') or row.get('time_to_plate_runner') or row.get('pace_runner')),
                        'pace_empty':     safe(row.get('pace_per_pitch') or row.get('time_to_plate') or row.get('pace')),
                        'pickoffs':       safe(row.get('pickoffs') or row.get('pickoff_attempts')),
                    }
                print(f'  Direct URL: {len(result)} pitchers')
        except Exception as e2:
            print(f'  Direct URL failed: {e2}')

        # Fallback: savant-extras
        if not result:
            try:
                from savant_extras import pitch_tempo
                df2 = pitch_tempo(SEASON)
                if not df2.empty:
                    for _, row in df2.iterrows():
                        pid = int(row.get('pitcher_id') or row.get('player_id') or 0)
                        if not pid: continue
                        result[pid] = {
                            'player_name':    row.get('pitcher_name') or row.get('player_name',''),
                            'team':           row.get('team_name',''),
                            'pace_runner_on': safe(row.get('pace_per_pitch_rascore') or row.get('time_to_plate_runner')),
                            'pace_empty':     safe(row.get('pace_per_pitch') or row.get('time_to_plate_empty')),
                            'pickoffs':       safe(row.get('pickoffs')),
                        }
                    print(f'  savant-extras: {len(result)} pitchers')
            except Exception as e3:
                print(f'  savant-extras fallback failed: {e3}')

        if result:
            write_json('savant-pitch-tempo.json', result)
            write_json('savant-pitcher-sb.json', result)
            files_updated += ['savant-pitch-tempo.json','savant-pitcher-sb.json']
        else:
            print('  pitch-tempo: no data from any source')
            errors.append('pitch-tempo')
    except Exception as e:
        print(f'  pitch-tempo error: {e}'); errors.append('pitch-tempo')

    # ── 9. BASERUNNING (pybaseball) ──
    try:
        print('\n[9/11] Baserunning stats...')
        # Use statcast running splits or OAA running
        df = pb.statcast_running_splits(SEASON, min_opp=10, bl=False)
        result = {}
        for _, row in df.iterrows():
            pid = int(row.get('player_id', 0) or 0)
            if not pid: continue
            result[pid] = {
                'player_name':  row.get('player_name',''),
                'sprint_speed': safe(row.get('sprint_speed')),
                'hp_to_1b':     safe(row.get('hp_to_1b')),
                'xbt_pct':      safe(row.get('xbt_pct') or row.get('extra_base_taken_pct')),
                'br_runs':      safe(row.get('baseRunning_runs') or row.get('br_runs_above_avg')),
            }
        write_json('savant-baserunning.json', result)
        files_updated.append('savant-baserunning.json')
    except Exception as e:
        print(f'  baserunning error (trying OAA): {e}')
        # Fallback: use sprint speed data as baserunning proxy
        try:
            sprint_path = os.path.join(DATA_DIR, 'savant-sb-leaders.json')
            if os.path.exists(sprint_path):
                import shutil
                shutil.copy(sprint_path, os.path.join(DATA_DIR, 'savant-baserunning.json'))
                files_updated.append('savant-baserunning.json')
                print('  baserunning: used sprint speed as fallback')
        except:
            errors.append('baserunning')

    # ── 10. META ──
    meta = {
        'updated': datetime.now(timezone.utc).isoformat(),
        'season':  SEASON,
        'files_updated': files_updated,
    }
    write_json('savant-meta.json', meta)
    files_updated.append('savant-meta.json')

    print(f'\n=== Done — {len(files_updated)} files updated ===')
    core_errors = [e for e in errors if e in ('hitter-expected','sprint','pitcher-expected')]
    if core_errors:
        print(f'Core errors: {core_errors}')
        sys.exit(1)
    elif errors:
        print(f'Non-critical errors (SB data partial): {errors}')

if __name__ == '__main__':
    main()
