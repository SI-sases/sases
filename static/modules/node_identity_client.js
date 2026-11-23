// static/modules/node_identity_client.js
// 节点身份：保存 node_id / manifest，并在登录后自动刷新。
const NODE_ID_KEY = 'sases_node_id';
const MANIFEST_KEY = 'sases_node_manifest';
const PROFILE_KEY = 'sases_node_profile';
const NAME_KEY = 'sases_node_name';

export function getNodeId() {
  return localStorage.getItem(NODE_ID_KEY) || '';
}

export function getNodeManifest() {
  return localStorage.getItem(MANIFEST_KEY) || '';
}

export function getNodeProfile() {
  return localStorage.getItem(PROFILE_KEY) || '';
}

export function getNodeName() {
  return localStorage.getItem(NAME_KEY) || '';
}

export function setNodeBundle(bundle) {
  const nodeId = String(bundle.node_id || '').trim();
  const manifest = String(bundle.manifest || '').trim();
  if (!nodeId || !manifest) {
    throw new Error('node_id or manifest missing');
  }
  localStorage.setItem(NODE_ID_KEY, nodeId);
  localStorage.setItem(MANIFEST_KEY, manifest);
  localStorage.setItem(PROFILE_KEY, String(bundle.profile || ''));
  localStorage.setItem(NAME_KEY, String(bundle.name || ''));
  return { nodeId, profile: bundle.profile || '' };
}

export function clearNodeIdentity() {
  localStorage.removeItem(NODE_ID_KEY);
  localStorage.removeItem(MANIFEST_KEY);
  localStorage.removeItem(PROFILE_KEY);
  localStorage.removeItem(NAME_KEY);
}

export async function refreshNodeManifest(token) {
  const nodeId = getNodeId();
  const bearer = token || localStorage.getItem('sases_token') || '';
  if (!nodeId || !bearer) return null;
  const resp = await fetch(`/node/manifest?node_id=${encodeURIComponent(nodeId)}`, {
    headers: { Authorization: `Bearer ${bearer}` }
  });
  if (!resp.ok) return null;
  const data = await resp.json();
  if (data.manifest) {
    localStorage.setItem(MANIFEST_KEY, data.manifest);
    if (data.manifest_payload?.profile) {
      localStorage.setItem(PROFILE_KEY, data.manifest_payload.profile);
    }
  }
  return data;
}

export async function applyCreator(nodeId, note) {
  const token = localStorage.getItem('sases_token') || '';
  const resp = await fetch('/node/creator/apply', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ node_id: nodeId, note: note || '' })
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
  return data;
}
