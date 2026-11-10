"""Generate synthetic real OOXML fixtures; never use personal documents."""
from pathlib import Path
from datetime import datetime,timezone
import io,zipfile
from docx import Document
from openpyxl import Workbook
from openpyxl.comments import Comment
from pptx import Presentation
from pptx.util import Inches
ROOT=Path(__file__).resolve().parent/'fixtures';ROOT.mkdir(exist_ok=True)
doc=Document();doc.add_heading('Metadata test',0);doc.add_paragraph('Original document body must be preserved.');doc.core_properties.author='Fixture Author';doc.core_properties.last_modified_by='Fixture Editor';doc.core_properties.revision=12;doc.save(ROOT/'sample.docx')
wb=Workbook();ws=wb.active;ws.title='Measurements';ws.append(['Value','Formula']);ws.append([7,'=A2*2']);ws['A2'].comment=Comment('Keep this comment text.','Fixture Author');wb.properties.creator='Fixture Author';wb.properties.lastModifiedBy='Fixture Editor';wb.save(ROOT/'sample.xlsx')
prs=Presentation();slide=prs.slides.add_slide(prs.slide_layouts[5]);slide.shapes.title.text='Original slide title';box=slide.shapes.add_textbox(Inches(1),Inches(2),Inches(7),Inches(1));box.text='Original slide content must be preserved.';prs.core_properties.author='Fixture Author';prs.core_properties.last_modified_by='Fixture Editor';prs.save(ROOT/'sample.pptx')
# Add explicit removable custom properties and template timestamps to each.
for p in ROOT.glob('sample.*'):
 with zipfile.ZipFile(p) as z:parts={n:z.read(n) for n in z.namelist()}
 custom='''<?xml version="1.0" encoding="UTF-8"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="2" name="InternalOwner"><vt:lpwstr>Fixture Private Marker</vt:lpwstr></property></Properties>'''
 rel='http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties'
 parts['docProps/custom.xml']=custom.encode();parts['_rels/.rels']=parts['_rels/.rels'].replace(b'</Relationships>',f'<Relationship Id="rIdFixtureCustom" Type="{rel}" Target="docProps/custom.xml"/></Relationships>'.encode());parts['[Content_Types].xml']=parts['[Content_Types].xml'].replace(b'</Types>',b'<Override PartName="/docProps/custom.xml" ContentType="application/vnd.openxmlformats-officedocument.custom-properties+xml"/></Types>')
 with zipfile.ZipFile(p,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for name,data in parts.items():z.writestr(name,data)
print('Generated DOCX, XLSX and PPTX synthetic fixtures.')
