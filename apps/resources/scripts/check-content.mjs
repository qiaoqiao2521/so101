import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
const records = JSON.parse(readFileSync(new URL('../src/data/resources.json', import.meta.url), 'utf8'));
const fields = ['id','title','description','project','category','format','level','url','source','checkedAt','tags'];
const ids = new Set();
const urls = new Set();
const projects = new Set(['SO101','FishBot','通用']);
const categories = new Set(['入门','硬件','软件环境','模型与仿真','学习工具']);
assert(Array.isArray(records) && records.length > 0, 'Resource catalog must contain records');
for (const record of records) {
  for (const key of fields) assert(record[key] != null, `${record.id}: missing ${key}`);
  assert(!ids.has(record.id), `Duplicate id: ${record.id}`); ids.add(record.id);
  assert(!urls.has(record.url), `Duplicate resource URL: ${record.url}`); urls.add(record.url);
  assert(projects.has(record.project), `${record.id}: unknown project`);
  assert(categories.has(record.category), `${record.id}: unknown category`);
  const url = new URL(record.url);
  assert(url.protocol === 'https:' && !url.username && !url.password, `${record.id}: public HTTPS URL required`);
  assert(!['localhost','127.0.0.1','0.0.0.0'].includes(url.hostname), `${record.id}: private URL`);
  assert(/^\d{4}-\d{2}-\d{2}$/.test(record.checkedAt), `${record.id}: invalid review date`);
  assert(Array.isArray(record.tags) && record.tags.every(t => typeof t === 'string'), `${record.id}: invalid tags`);
}
console.log(JSON.stringify({ resources: records.length, projects: [...projects], validation: 'passed' }));
