// Original adapter for a version-dependent Feishu web application model.
// Use inside an authenticated page. Never replace normal permission/sync checks.
function feishuPageAdapter(payload) {
  const clone = value => JSON.parse(JSON.stringify(value));
  const canonical = value => Array.isArray(value) ? value.map(canonical) :
    value && typeof value === 'object' ? Object.fromEntries(Object.keys(value).sort().map(k => [k, canonical(value[k])])) : value;
  const equal = (a, b) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));
  const base = window.bitableStore;
  if (!base?.modelOperator?.getTableById) throw new Error('ADAPTER_UNAVAILABLE: use the visible UI');
  const table = base.modelOperator.getTableById(payload.table_id);
  if (!table) throw new Error('TABLE_UNAVAILABLE: choose the actual data table in the UI');
  const count = table.getAllRecordCount();
  if (count > 5000) throw new Error('TABLE_TOO_LARGE: define a smaller authorized workflow');
  if (table.getLoadedRecordCount() !== count || Array.from(table.getRecordIds()).length !== count)
    throw new Error('INCOMPLETE_TABLE: load all authorized records before planning');
  const snapshot = () => ({
    url: location.href, tableId: table.id, viewId: new URL(location.href).searchParams.get('view'),
    name: table.name, revision: table.rev, recordCount: count,
    fields: Object.values(table.fields).map(f => {
      const data = {id: f.id, name: f.name, type: f.type};
      if (f.property !== undefined) data.property = clone(f.property);
      return data;
    }),
    records: Array.from(table.getRecordIds()).map(id => ({id, data: clone(table.getRecordDataById(id))})),
  });
  if (payload.op === 'snapshot') return snapshot();
  const queue = base._bitableSync?.queue;
  if (typeof queue?.getQueueStatus !== 'function') throw new Error('SYNC_ADAPTER_UNAVAILABLE');
  const status = queue.getQueueStatus();
  if (typeof status.localOperationLen !== 'number' || typeof status.isSubmitting !== 'boolean' || typeof status.isStoring !== 'boolean')
    throw new Error('SYNC_STATUS_UNSUPPORTED');
  if (payload.op === 'status') return status;
  if (status.localOperationLen !== 0 || status.isSubmitting || status.isStoring)
    throw new Error('PENDING_USER_OPERATIONS: wait for existing changes to save');
  const plan = payload.plan;
  if (!plan?.ready || !plan.records?.length || plan.record_count !== count || plan.table_id !== table.id)
    throw new Error('PLAN_NOT_READY_OR_TARGET_CHANGED');
  const group = table.getFieldById(plan.field_id);
  if (group?.type !== 3) throw new Error('FIELD_TYPE_CHANGED');
  if (typeof base.commandManager?.execute !== 'function' || typeof group.toJSON !== 'function')
    throw new Error('WRITE_ADAPTER_UNAVAILABLE');
  for (const row of plan.records) {
    const data = table.getRecordDataById(row.record_id);
    if (!data || !equal(data[plan.title_field_id] ?? null, row.expected_title_cell ?? null) ||
        !equal(data[plan.description_field_id] ?? null, row.expected_description_cell ?? null))
      throw new Error('CONCURRENT_REQUIREMENT_CHANGE');
    const expected = payload.expected_values?.[row.record_id] ?? row.old_value;
    if (!equal(data[plan.field_id]?.value ?? null, expected ?? null))
      throw new Error('CONCURRENT_MODULE_CHANGE');
  }
  if (payload.op === 'add_options') {
    const current = snapshot().fields.find(f => f.id === plan.field_id);
    if (!equal(current, plan.baseline_field)) throw new Error('CONCURRENT_SCHEMA_CHANGE');
    const data = clone(group.toJSON());
    const used = new Set(data.property.options.map(o => o.id));
    const alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    const added = plan.new_modules.map((name, i) => {
      let id;
      do { const bytes = crypto.getRandomValues(new Uint8Array(7));
        id = 'opt' + [...bytes].map(n => alphabet[n % alphabet.length]).join('');
      } while (used.has(id));
      used.add(id); return {id, name, color: i % 35};
    });
    if (!added.length) return {unchanged: true};
    data.property.options.push(...added);
    const result = base.commandManager.execute({cmd: 'SetFieldAttr', tableId: table.id,
      viewId: plan.view_id, fieldId: plan.field_id, data});
    return {result: result?.result, added, observed: clone(group.property.options)};
  }
  if (payload.op !== 'set_values') throw new Error('UNKNOWN_OPERATION');
  if (!payload.expected_field || !equal(snapshot().fields.find(f => f.id === plan.field_id), payload.expected_field))
    throw new Error('CONCURRENT_SCHEMA_CHANGE');
  const options = new Map(group.property.options.map(o => [o.name, o.id]));
  const chosen = payload.record_ids;
  if (!Array.isArray(chosen) || !chosen.length || new Set(chosen).size !== chosen.length) throw new Error('INVALID_RECORD_SELECTION');
  const data = {}, planned = new Map(plan.records.map(r => [r.record_id, r]));
  for (const id of chosen) {
    const row = planned.get(id);
    if (!row) throw new Error('RECORD_OUTSIDE_PLAN');
    const value = options.get(row.module);
    if (!value) throw new Error('MISSING_SAVED_OPTION');
    data[id] = {[plan.field_id]: {type: 3, value}};
  }
  const result = base.commandManager.execute({cmd: 'SetRecords', tableId: table.id, viewId: plan.view_id, data});
  return {result: result?.result, requested: chosen.length};
}
