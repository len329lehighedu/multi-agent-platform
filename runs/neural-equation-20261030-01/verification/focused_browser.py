"""Focused live checks absent from initial happy-path browser suite."""
import json
import math
import time
from playwright.sync_api import sync_playwright

def main():
    checks=[];errors=[];started=time.perf_counter()
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        context=browser.new_context(viewport={'width':1366,'height':1000});page=context.new_page()
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('console',lambda message:errors.append(message.text) if message.type=='error' else None)
        page.goto('http://127.0.0.1:8088/',wait_until='networkidle')
        page.wait_for_function("window.Bokeh && Bokeh.documents.length && Bokeh.documents[0].get_model_by_name('train')")
        def model(name,expression):
            return page.evaluate("([name,expr])=>Function('item','return '+expr)(Bokeh.documents[0].get_model_by_name(name))",[name,expression])
        def wait(expression):page.wait_for_function(expression,timeout=30000)
        def upload(text):page.locator('input[type=file]').set_input_files({'name':'qa.csv','mimeType':'text/csv','buffer':text.encode()})
        def numeric(name,value):
            field=page.locator(f'input[name="{name}"]');field.fill(str(value));field.press('Tab')
        upload('duplicate,duplicate\n'+'1,2\n'*25)
        wait("Bokeh.documents[0].get_model_by_name('status').text.startsWith('Upload rejected')")
        assert model('target','item.value')=='target'
        checks.append('Malformed duplicate-header upload rejected without replacing existing selection')
        valid='a,b,y\n'+'\n'.join(f'{i/10},{math.sin(i)},{2*i/10+math.sin(i)+1}' for i in range(30))+'\n,2,3\n1,nope,4\n'
        upload(valid)
        wait("Bokeh.documents[0].get_model_by_name('target').value === 'y'")
        search=page.locator('input[type=search]');search.fill('b');search.press('Enter');search.press('Tab')
        wait("Bokeh.documents[0].get_model_by_name('features').value.includes('b')")
        page.locator('select[name=solver]').select_option('adam')
        wait("!Bokeh.documents[0].get_model_by_name('learning_rate').disabled")
        numeric('learning_rate',.01);numeric('max_iter',20)
        page.get_by_role('button',name='Train neural network',exact=True).click()
        wait("Bokeh.documents[0].get_model_by_name('train').disabled")
        assert model('status','item.text').startswith('Training')
        assert model('upload','item.disabled')
        wait("Bokeh.documents[0].get_model_by_name('status').text.startsWith('Complete')")
        assert len(model('observations','item.data.x'))==30
        assert '30 / 2' in model('metrics','item.text')
        assert len(model('loss','item.data.objective'))==20
        assert model('nn_curve','item.data.x.length')==0
        assert model('identity_line','item.data.x.length')==2
        checks.append('Visible feature selection, selected-cell row dropping, adam applicability, busy lock, multifeature plot and loss all update')
        previous=model('metrics','item.text')
        page.locator('select[name=solver]').select_option('lbfgs')
        wait("Bokeh.documents[0].get_model_by_name('learning_rate').disabled")
        assert 'pending' in model('status','item.text').lower()
        assert model('metrics','item.text')==previous
        numeric('max_iter',100);numeric('equation_degree',4)
        page.set_viewport_size({'width':390,'height':844})
        page.get_by_role('button',name='Train neural network',exact=True).click()
        wait("Bokeh.documents[0].get_model_by_name('status').text.startsWith('Complete')")
        assert model('loss','item.data.objective.length')==0
        assert model('equation','item.text').count('*')>10
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
        for canvas in page.locator('canvas').all():
            box=canvas.bounding_box()
            if box:assert box['x']>=-1 and box['x']+box['width']<=391,box
        checks.append('Committed results stay stale until Train; lbfgs clears loss; trained 390px multifeature/long equation has no page or canvas overflow')
        previous=model('metrics','item.text');old_data=model('observations','Array.from(item.data.x)')
        upload(valid+'inf,2,3\n')
        wait("Bokeh.documents[0].get_model_by_name('preview').text.includes('33 raw rows')")
        page.get_by_role('button',name='Train neural network',exact=True).click()
        wait("Bokeh.documents[0].get_model_by_name('status').text.includes('infinity')")
        assert model('metrics','item.text')==previous
        assert model('observations','Array.from(item.data.x)')==old_data
        assert not model('train','item.disabled')
        checks.append('Explicit infinity fails before training with actionable row/column message, prior results retained')
        assert not errors,errors
        browser.close()
    print(json.dumps({'status':'pass','checks':checks,'errors':errors,'suite_seconds':time.perf_counter()-started},indent=2))

if __name__=='__main__':main()
