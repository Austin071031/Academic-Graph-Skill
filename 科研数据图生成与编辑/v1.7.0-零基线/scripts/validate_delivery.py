#!/usr/bin/env python3
"""Reopen explicitly required actual artifacts. Missing files never pass as completed delivery."""
import argparse
import hashlib
import importlib.util
import json
import math
import pathlib
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET


def validate(root, manifest):
    root=pathlib.Path(root).resolve()
    entries=manifest['artifacts']
    if not isinstance(entries,list) or not entries:
        raise ValueError('artifacts must be a nonempty list read from the actual workorder')
    checks=[]
    def record(path,name,ok,detail):
        checks.append({'path':path,'check':name,'passed':ok,'detail':detail})
    for entry in entries:
        relative=entry['path'];fmt=entry['format'].lower()
        path=(root/relative).resolve()
        if root not in path.parents:
            raise ValueError('Delivery path must be a file under output root: '+relative)
        if not path.is_file() or path.stat().st_size==0:
            record(relative,'exists',False,'Missing or empty required file');continue
        blob=path.read_bytes()
        record(relative,'exists',True,{'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest()})
        try:
            if fmt=='svg':
                svg=ET.fromstring(blob)
                record(relative,'svg_xml',svg.tag=='{http://www.w3.org/2000/svg}svg',svg.tag)
                texts=[e for e in svg.iter() if e.tag.endswith('}text')]
                record(relative,'native_text',bool(texts),'SVG labels must remain editable; XML alone does not prove scientific editability')
                ids=[e.get('id') for e in svg.iter() if e.get('id')]
                record(relative,'unique_ids',len(ids)==len(set(ids)),len(ids))
                for key in ['width','height']:
                    target=entry.get(key+'_mm')
                    if target is None:continue
                    raw=svg.get(key,'')
                    try:actual=float(raw[:-2]) if raw.endswith('mm') else float(raw[:-2])*25.4 if raw.endswith('in') else float(raw[:-2])*25.4/72 if raw.endswith('pt') else float(raw[:-2])*25.4/96 if raw.endswith('px') else float(raw)*25.4/96
                    except ValueError:actual=None
                    record(relative,key+'_mm',actual is not None and abs(actual-target)<.2,{'actual':actual,'required':target})
            elif fmt in ['png','tiff','jpg','jpeg']:
                if not importlib.util.find_spec('PIL'):
                    record(relative,'image_reopen',None,'Pillow unavailable; not verified');continue
                from PIL import Image
                with Image.open(path) as im:
                    im.load()
                    expected='JPEG' if fmt in ['jpg','jpeg'] else fmt.upper()
                    record(relative,'image_format',im.format==expected,{'format':im.format,'pixels':list(im.size),'mode':im.mode,'dpi':im.info.get('dpi')})
                    if entry.get('dpi'):
                        dpi=entry['dpi'];actual=im.info.get('dpi')
                        record(relative,'dpi_metadata',bool(actual) and all(abs(float(v)-dpi)<1 for v in actual[:2]),{'actual':actual,'required':dpi})
                        for axis,key in enumerate(['width_mm','height_mm']):
                            if key in entry:
                                expected_pixels=entry[key]/25.4*dpi
                                record(relative,key+'_pixels',abs(im.size[axis]-expected_pixels)<=1,{'actual':im.size[axis],'required':expected_pixels})
                    if entry.get('mode'):record(relative,'color_mode',im.mode==entry['mode'],{'actual':im.mode,'required':entry['mode']})
            elif fmt=='pdf':
                record(relative,'pdf_signature',blob.startswith(b'%PDF-'),blob[:8].decode('ascii','replace'))
                if importlib.util.find_spec('fitz'):
                    import fitz
                    with fitz.open(path) as doc:
                        record(relative,'pdf_pages',len(doc)>0,len(doc))
                        for page in doc:
                            pix=page.get_pixmap(matrix=fitz.Matrix(.5,.5))
                            record(relative,'pdf_render',pix.width>0 and pix.height>0,{'page':page.number+1,'render_pixels':[pix.width,pix.height]})
                            for key,actual in [('width_mm',page.rect.width/72*25.4),('height_mm',page.rect.height/72*25.4)]:
                                if key in entry:record(relative,key,abs(actual-entry[key])<.2,{'actual':actual,'required':entry[key]})
                elif shutil.which('pdftoppm'):
                    with tempfile.TemporaryDirectory(prefix='pdf-check-') as td:
                        out=pathlib.Path(td)/'preview'
                        r=subprocess.run(['pdftoppm','-f','1','-singlefile','-scale-to','300','-png',str(path),str(out)],capture_output=True,text=True,timeout=40)
                        record(relative,'pdf_render',r.returncode==0 and out.with_suffix('.png').is_file(),r.stderr[-1000:])
                    if 'width_mm' in entry or 'height_mm' in entry:record(relative,'pdf_physical_size',None,'Use pdfinfo to verify dimensions; fallback only rendered first page')
                else:record(relative,'pdf_reopen_render',None,'No PDF parser/renderer available; not verified')
            elif fmt=='json':
                json.loads(blob);record(relative,'json_parse',True,'Parsed actual file')
            elif fmt in ['pptx','docx','xlsx']:
                import zipfile
                with zipfile.ZipFile(path) as z:
                    record(relative,'office_container',z.testzip() is None,len(z.namelist()))
                record(relative,'office_native_editability_and_render',None,'Container validity is insufficient; inspect actual native objects and actual PDF/PNG previews')
            else:record(relative,'format_validation',None,'Unsupported format; inspect with native tool')
        except Exception as e:record(relative,'reopen',False,str(e))
    failed=any(c['passed'] is False for c in checks)
    incomplete=any(c['passed'] is None for c in checks)
    return {'status':'failed' if failed else 'needs_review' if incomplete else 'passed','checks':checks,
            'scope':'Actual required files and measured formats only. Scientific correctness, source-preserving edits, font embedding, colorspace profiles and visual collisions require separate checks.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True);p.add_argument('--manifest',required=True);p.add_argument('--out',required=True)
    a=p.parse_args()
    try:report=validate(a.root,json.loads(pathlib.Path(a.manifest).read_text()))
    except Exception as e:report={'status':'failed','error':str(e)}
    dest=pathlib.Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'out':str(dest)}))
    return 0 if report['status']=='passed' else 2 if report['status']=='needs_review' else 1


if __name__=='__main__':sys.exit(main())
