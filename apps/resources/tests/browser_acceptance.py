#!/usr/bin/env python3
"""Read-only production UI acceptance through the isolated background browser.

No browser packages are installed. Requires the user's browser-bg launcher.
Network method coverage is intentionally outside this check.
"""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = Path.home() / '.local/bin/browser-bg'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('--label', default='preview-final')
    parser.add_argument('--session', default='robot-resource-qa')
    args = parser.parse_args()
    output = ROOT / 'output/qa'
    output.mkdir(parents=True, exist_ok=True)
    evidence = {'url': args.url, 'label': args.label, 'checks': [],
                'network_boundary': 'No complete network-method capture; no zero-POST claim.'}

    def bb(*command):
        process = subprocess.run([str(LAUNCHER), args.session, *command, '--json'],
                                 text=True, capture_output=True, timeout=30)
        if process.returncode:
            raise RuntimeError(f'{command}: {process.stderr or process.stdout}')
        response = json.loads(process.stdout)
        if not response['success']:
            raise RuntimeError(response)
        return response['data']

    def ev(script):
        return bb('eval', script)['result']

    def record(name, actual, condition=True):
        evidence['checks'].append({'name': name, 'passed': bool(condition), 'actual': actual})
        print(f'{"PASS" if condition else "FAIL"}: {name}', flush=True)
        if not condition:
            raise AssertionError(f'{name}: {actual}')

    def state():
        return ev('''({url: location.href,
          query: document.querySelector('#resource-query').value,
          category: document.querySelector('#resource-category').value,
          project: document.querySelector('[name="project"]:checked').value,
          titles: [...document.querySelectorAll('[data-resource-item]')]
            .filter(e=>!e.hidden).map(e=>e.querySelector('h3 a').textContent.trim()),
          count: document.querySelector('[data-resource-count]').textContent,
          empty: !document.querySelector('[data-resource-empty]').hidden})''')

    def geometry():
        return ev('''({width: innerWidth, height: innerHeight,
          documentWidth: document.documentElement.scrollWidth,
          bodyWidth: document.body.scrollWidth,
          overflowing: [...document.querySelectorAll('body *')].filter(e=>{
            const r=e.getBoundingClientRect(),s=getComputedStyle(e);
            return r.width>0 && r.height>0 && s.visibility!=='hidden' &&
              !e.closest('[hidden]') && (r.right>innerWidth+1 || r.left < -1);
          }).slice(0,8).map(e=>({tag:e.tagName,class:e.className,
            text:e.textContent.trim().slice(0,50)}))})''')

    def capture(name):
        path = output / f'{args.label}-{name}.png'
        bb('screenshot', str(path))
        return str(path)

    try:
        bb('open', args.url)
        bb('set', 'viewport', '1440', '1000')
        bb('wait', '[data-resource-filters]:not([hidden])')
        initial = state()
        record('24 resources initially visible', initial, len(initial['titles']) == 24)
        box = geometry()
        record('desktop 1440 has no horizontal overflow', box,
               box['documentWidth'] == box['width'] and box['bodyWidth'] == box['width'])
        record('desktop screenshot', capture('desktop'))

        bb('check', '[name="project"][value="FishBot"]')
        fishbot = state()
        record('FishBot filter', fishbot, len(fishbot['titles']) == 6 and
               any('FishBot 建图与导航源码' in title for title in fishbot['titles']) and
               any('Nav2 Jazzy 调参指南' in title for title in fishbot['titles']))
        bb('check', '[name="project"][value="SO101"]')
        bb('select', '#resource-category', '硬件')
        hardware = state()
        record('SO101 hardware combination', hardware, len(hardware['titles']) == 3)
        bb('fill', '#resource-query', 'STL')
        filtered = state()
        record('project category keyword combination', filtered,
               len(filtered['titles']) == 1 and 'STL 打印零件' in filtered['titles'][0])
        bb('reload')
        bb('wait', '[data-resource-filters]:not([hidden])')
        restored = state()
        record('refresh restores URL filters', restored, restored == filtered)
        record('filtered screenshot', capture('filtered'))

        bb('fill', '#resource-query', '不存在资料qa20261018')
        empty = state()
        record('empty results show recovery action', empty,
               len(empty['titles']) == 0 and empty['empty'])
        bb('click', '[data-resource-empty-reset]')
        reset = state()
        record('empty reset restores all and clears URL filters', reset,
               len(reset['titles']) == 24 and not reset['empty'] and
               reset['query'] == reset['category'] == reset['project'] == '' and
               '?' not in reset['url'])

        bb('click', '[data-open-modal]')
        bb('wait', '.pagefind-ui__search-input')
        bb('fill', '.pagefind-ui__search-input', '交付')
        bb('wait', '.pagefind-ui__result-link[href*="/delivery/"]')
        search = ev('''[...document.querySelectorAll('.pagefind-ui__result-link')]
          .map(e=>({text:e.textContent.trim(),href:e.href}))''')
        record('native fulltext search finds Chinese delivery guide', search,
               any('/delivery/' in row['href'] and '交付' in row['text'] for row in search))
        record('search screenshot', capture('search'))
        bb('click', '.pagefind-ui__result-link[href*="/delivery/"]')
        bb('wait', 'h1')
        title = ev('({url:location.href, title:document.querySelector("h1").textContent})')
        record('search result opens delivery guide', title,
               '/delivery/' in title['url'] and '交付' in title['title'])

        bb('open', args.url)
        bb('set', 'viewport', '390', '844')
        bb('wait', '[data-resource-filters]:not([hidden])')
        box = geometry()
        record('mobile 390 has no horizontal overflow', box,
               box['documentWidth'] == box['width'] and box['bodyWidth'] == box['width'])
        record('mobile screenshot', capture('mobile'))
        bb('check', '[name="project"][value="SO101"]')
        bb('select', '#resource-category', '硬件')
        bb('fill', '#resource-query', 'STL')
        mobile_filtered = state()
        record('mobile combined filter', mobile_filtered,
               len(mobile_filtered['titles']) == 1 and 'STL 打印零件' in mobile_filtered['titles'][0])
        bb('reload')
        restored = state()
        record('mobile refresh restores filters', restored, restored == mobile_filtered)
        bb('click', '[data-resource-reset]')
        record('mobile reset', state(), len(state()['titles']) == 24)
        bb('click', '[data-open-modal]')
        bb('wait', '.pagefind-ui__search-input')
        bb('fill', '.pagefind-ui__search-input', '校准')
        bb('wait', '.pagefind-ui__result-link[href*="/so101/assembly/"]')
        search = ev('''[...document.querySelectorAll('.pagefind-ui__result-link')]
          .map(e=>({text:e.textContent.trim(),href:e.href}))''')
        record('mobile native Chinese search finds assembly guide', search,
               any('/so101/assembly/' in row['href'] for row in search))
        record('mobile search screenshot', capture('mobile-search'))
        bb('click', '[data-close-modal]')

        bb('open', args.url.rstrip('/') + '/delivery/')
        box = geometry()
        record('mobile delivery table does not overflow document', box,
               box['documentWidth'] == box['width'])
        bb('click', '[popovertarget="starlight__sidebar"]')
        bb('wait', '#starlight__sidebar:popover-open')
        record('mobile menu screenshot', capture('mobile-menu'))
        bb('click', '#starlight__sidebar a[href="/fishbot/navigation/"]')
        bb('wait', 'h1')
        navigation = ev('''({url:location.href,title:document.querySelector('h1').textContent,
          menuOpen: Boolean(document.querySelector('#starlight__sidebar:popover-open'))})''')
        record('mobile menu opens FishBot navigation guide', navigation,
               '/fishbot/navigation/' in navigation['url'] and
               '导航' in navigation['title'] and not navigation['menuOpen'])
        record('mobile guide screenshot', capture('mobile-guide'))

        routes = ['/start-here/', '/so101/', '/so101/assembly/', '/so101/simulation/',
                  '/fishbot/', '/fishbot/environment/', '/fishbot/navigation/',
                  '/common/glossary/', '/delivery/', '/updates/', '/sources/']
        route_boxes = []
        for route in routes:
            bb('open', args.url.rstrip('/') + route)
            box = geometry()
            box['route'] = route
            route_boxes.append(box)
        record('all 11 guide pages fit mobile width 390', route_boxes,
               all(row['documentWidth'] == row['width'] for row in route_boxes))

        bb('open', args.url)
        bb('set', 'viewport', '320', '740')
        box = geometry()
        record('small mobile 320 has no horizontal overflow', box,
               box['documentWidth'] == box['width'] and box['bodyWidth'] == box['width'])
        links = ev('''({resources:[...document.querySelectorAll('[data-resource-item] h3 a')]
          .map(e=>({title:e.textContent.trim(),href:e.href})),
          controls:[...document.querySelectorAll('button,input[type="submit"]')]
            .map(e=>e.textContent.trim())})''')
        expected_links = [row['url'] for row in json.loads((ROOT/'src/data/resources.json').read_text())]
        record('24 rendered official resource destinations match source records', links,
               [row['href'] for row in links['resources']] == expected_links and
               all(row['href'].startswith('https://') for row in links['resources']))
        record('homepage has only search and reset buttons', links['controls'],
               set(links['controls']) <= {'搜索CtrlK', '取消', 'Clear', '重置筛选', '查看全部资料'})
        errors = bb('errors')
        record('no browser page errors', errors.get('errors', []), not errors.get('errors'))
        console = bb('console')
        record('browser console', console.get('messages', []),
               not any(row.get('type') == 'error' for row in console.get('messages', [])))
    finally:
        path = output / f'{args.label}-results.json'
        path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
        print(f'Evidence: {path}', flush=True)


if __name__ == '__main__':
    main()
