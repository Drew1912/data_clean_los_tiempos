"use client";
import { useEffect, useState, type FormEvent } from 'react';
import { consultarUsuarios, guardarUsuario, type ManagedUser, type UsersPage } from '@/lib/api';
import { useSessionUser } from './AuthGate';
import { Pager } from './Results';

const EMPTY:UsersPage={datos:[],roles:[],total:0,pagina:1,tamano:25};
const LABELS:Record<string,string>={cargar:'Cargar archivos',consultar:'Consultar cargas y registros',procesar:'Configurar columnas y ejecutar limpieza',comparar:'Comparar facturas',descargar:'Descargar Excel limpio y observaciones',usuarios:'Administrar usuarios',auditoria:'Consultar auditoría'};
export default function UsersWorkspace({active}:{active:boolean}) {
 const session=useSessionUser(), allowed=session?.permisos.includes('usuarios');
 const [data,setData]=useState(EMPTY),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
 const [editing,setEditing]=useState<ManagedUser|null>(null),[name,setName]=useState(''),[role,setRole]=useState('consulta'),[password,setPassword]=useState(''),[enabled,setEnabled]=useState(true),[audit,setAudit]=useState(false);
 async function load(page=1){setBusy(true);setError('');try{setData(await consultarUsuarios(page));}catch(e){setError(e instanceof Error?e.message:'No se pudieron consultar los usuarios.');}finally{setBusy(false);}}
 useEffect(()=>{if(active&&allowed)void load();},[active,allowed]);
 function reset(){setEditing(null);setName('');setRole('consulta');setPassword('');setEnabled(true);setAudit(false);}
 function edit(user:ManagedUser){setEditing(user);setName(user.nombre);setRole(user.rol);setEnabled(user.activo);setAudit(user.puede_ver_auditoria);setPassword('');setMessage('');setError('');document.getElementById('user-form-title')?.scrollIntoView({block:'center'});}
 async function save(event:FormEvent){event.preventDefault();setBusy(true);setError('');setMessage('');try{
  await guardarUsuario({rol:role,activo:enabled,puede_ver_auditoria:role==='administrador'&&audit,...(!editing?{nombre:name}:{}),...(!editing||password?{contrasena:password}:{})},editing?.id);
  setPassword('');
  if(editing?.id===session?.id){window.dispatchEvent(new Event('dataclean:sesion-vencida'));return;}
  setMessage(editing?'Usuario actualizado. Sus sesiones anteriores quedaron revocadas.':'Usuario creado. Ya puede ingresar con las credenciales asignadas.');reset();setData(await consultarUsuarios(data.pagina));
 }catch(e){setError(e instanceof Error?e.message:'No se pudo guardar el usuario.');}finally{setBusy(false);}}
 if(!allowed)return <section className="panel"><h2>Acceso restringido</h2><p>Solo el administrador puede gestionar usuarios.</p></section>;
 const chosen=data.roles.find(r=>r.codigo===role);
 const protectedAccount=!!editing&&(editing.id===1||editing.id===session?.id);
 return <section className="panel" aria-labelledby="users-title">
  <div className="panel-heading"><h2 id="users-title">Usuarios y permisos</h2><button className="secondary" disabled={busy} onClick={()=>void load(data.pagina)}>Actualizar usuarios</button></div>
  <p>Cada cuenta consulta únicamente sus propias cargas. El administrador puede supervisar todas. Los permisos dependen del rol asignado.</p>
  {message&&<p role="status" className="info-box">{message}</p>}{error&&<p role="alert" className="error-box">{error}</p>}
  <form onSubmit={save} className="user-form"><h3 id="user-form-title">{editing?`Editar usuario: ${editing.nombre}`:'Añadir usuario'}</h3>
   <div className="audit-filters">
    <label>Usuario<input aria-label="Nombre del usuario" value={name} onChange={e=>setName(e.target.value)} required disabled={busy||!!editing} pattern="[a-z][a-z0-9._-]{2,49}" minLength={3} maxLength={50} autoComplete="off"/></label>
    <label>Rol<select aria-label="Rol del usuario" disabled={busy||protectedAccount} value={role} onChange={e=>{setRole(e.target.value);setAudit(e.target.value==='administrador');}}>{data.roles.map(r=><option key={r.codigo} value={r.codigo}>{r.nombre}</option>)}</select></label>
    <label>{editing?'Contraseña nueva (opcional)':'Contraseña inicial'}<input type="password" aria-label="Contraseña del usuario" required={!editing} disabled={busy} minLength={8} maxLength={128} value={password} onChange={e=>setPassword(e.target.value)} autoComplete="new-password"/></label>
   </div>
   <p className="note">Usuario: 3–50 caracteres en minúsculas, empieza por letra. Contraseña nueva: 8–128 caracteres. Al editar, deja la contraseña vacía para conservarla.</p>
   <label className="check-label"><input type="checkbox" checked={enabled} disabled={busy||protectedAccount} onChange={e=>setEnabled(e.target.checked)}/>Cuenta activa</label>
   {role==='administrador'&&<label className="check-label"><input type="checkbox" checked={audit} disabled={busy} onChange={e=>setAudit(e.target.checked)}/>Permitir consulta de auditoría</label>}
   <p><b>Permisos de este rol:</b> {chosen?.permisos.filter(p=>p!=='auditoria'||audit).map(p=>LABELS[p]??p).join(' · ')||'Cargando roles…'}</p>
   <p className="note">Configurar y limpiar no permite editar facturas manualmente. Los usuarios de solo lectura o descarga podrán abrir cargas propias que ya tengan asignadas por su actividad anterior.</p>
   <div className="actions"><button type="submit" disabled={busy||!data.roles.length}>{editing?'Guardar cambios del usuario':'Crear usuario'}</button>{editing&&<button type="button" className="secondary" disabled={busy} onClick={reset}>Cancelar edición</button>}</div>
  </form>
  <div className="table-scroll"><table><caption>Usuarios registrados</caption><thead><tr><th>Usuario</th><th>Rol</th><th>Estado</th><th>Permisos</th><th>Acción</th></tr></thead><tbody>{data.datos.map(u=><tr key={u.id}><td>{u.nombre}</td><td>{data.roles.find(r=>r.codigo===u.rol)?.nombre??u.rol}</td><td>{u.activo?'Activo':'Inactivo'}</td><td>{u.permisos.map(p=>LABELS[p]??p).join(' · ')}</td><td><button className="secondary" disabled={busy} onClick={()=>edit(u)}>Editar {u.nombre}</button></td></tr>)}</tbody></table></div>
  <Pager data={data} busy={busy} change={p=>void load(p)}/>
  <p className="note">Desactivar conserva las cargas y el historial. Cambiar rol, estado, permiso de auditoría o contraseña revoca las sesiones del usuario. No se permite desactivar ni quitar el rol de la cuenta admin original o de tu propia cuenta administradora.</p>
 </section>;
}
