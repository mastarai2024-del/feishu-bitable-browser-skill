import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/feishu-bitable-browser/scripts'))
import browser
from workflow import make_plan
from playwright.sync_api import sync_playwright


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler=functools.partial(QuietHandler,directory=str(ROOT/'tests/fixtures'))
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.pw=sync_playwright().start();cls.browser=cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.pw.stop();cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def setUp(self):
        self.context=self.browser.new_context();self.page=self.context.new_page()
        self.page.goto(f'http://127.0.0.1:{self.server.server_port}/base.html?table=tblFixture&view=vewFixture')
        self.before=browser.call(self.page,'snapshot','tblFixture')
        source=[{'row':i+2,'module':'First' if i!=1 else 'Second','title':r['data']['fldTitle']['value'][0]['text'],
                 'description':r['data']['fldDesc']['value'][0]['text']} for i,r in enumerate(self.before['records'])]
        self.plan=make_plan(source,self.before,'业务模块','需求标题','需求描述')

    def tearDown(self):self.context.close()

    def test_actual_browser_pilot_and_refresh_persistence(self):
        with tempfile.TemporaryDirectory() as directory:
            result=browser.apply_plan(self.page,self.plan,Path(directory)/'run')
            self.assertTrue(result['passed']);self.assertEqual(result['matched'],3)
            state=self.page.evaluate('fixtureRead()')
            self.assertEqual(state['calls'],['SetFieldAttr','SetRecords','SetRecords'])
            self.assertEqual(len(state['fields'][2]['property']['options']),3)
            self.assertEqual(json.loads((Path(directory)/'run/journal.json').read_text())['status'],'verified')

    def test_concurrent_title_blocks_before_first_write(self):
        self.page.evaluate('fixtureAlterTitle()')
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(Exception):browser.apply_plan(self.page,self.plan,Path(directory)/'run')
        self.assertEqual(self.page.evaluate('fixtureRead().calls.length'),0)

    def test_sparse_empty_description_can_be_matched(self):
        self.page.evaluate("delete window.bitableStore.modelOperator.getTableById('tblFixture').getRecordDataById('recOne').fldDesc;localStorage.setItem('fixture-state',JSON.stringify(fixtureRead()));")
        before=browser.call(self.page,'snapshot','tblFixture')
        source=[]
        for i,r in enumerate(before['records']):
            source.append({'row':i+2,'module':'First','title':r['data']['fldTitle']['value'][0]['text'],
                           'description':r['data'].get('fldDesc',{}).get('value',[{'text':''}])[0]['text']})
        plan=make_plan(source,before,'业务模块','需求标题','需求描述')
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(browser.apply_plan(self.page,plan,Path(directory)/'run')['passed'])

    def test_incomplete_or_pending_state_blocks_write(self):
        self.page.evaluate('fixtureControls.incomplete=true')
        with self.assertRaises(Exception):browser.call(self.page,'snapshot','tblFixture')
        self.page.evaluate('fixtureControls.incomplete=false;fixtureControls.pending=true')
        with self.assertRaises(Exception):browser.call(self.page,'add_options','tblFixture',plan=self.plan)
        self.assertEqual(self.page.evaluate('fixtureRead().calls.length'),0)

    def test_unknown_save_stops_without_duplicate_submission(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(browser,'drain',side_effect=RuntimeError('UNKNOWN_SAVE_STATE')):
                with self.assertRaises(RuntimeError):browser.apply_plan(self.page,self.plan,Path(directory)/'run')
            self.assertEqual(self.page.evaluate('fixtureRead().calls.length'),1)
            self.assertEqual(json.loads((Path(directory)/'run/journal.json').read_text())['status'],'needs_reconciliation')

    def test_denied_write_not_reported_as_saved(self):
        self.page.evaluate('fixtureControls.deny=true')
        # The denied flag is reset by refresh, but the rejected schema never persists.
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):browser.apply_plan(self.page,self.plan,Path(directory)/'run')
        self.assertEqual(self.page.evaluate('fixtureRead().calls.length'),0)


if __name__=='__main__':unittest.main()
