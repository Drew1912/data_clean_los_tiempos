"use client";
import {useEffect,useState} from 'react';
import {consultarCargas,type SavedLot} from '@/lib/api';
import type {Page} from '@/types/facturacion';
import {Pager} from './Results';
export default function LotPicker({active,busy,open,revision}:{active:boolean;busy:boolean;open:(id:string)=>Promise<void>;revision:number}){
 const [data,setData]=useState<Page<SavedLot>>({datos:[],total:0,pagina:1,tamano:10}),[loading,setLoading]=useState(false),[error,setError]=useState('');
 async function load(page=1){setLoading(true);setError('');try{setData(await consultarCargas(page));}catch(e){setError(e instanceof Error?e.message:'No se pudieron consultar las cargas.');}finally{setLoading(false);}}
 useEffect(()=>{if(active)void load();},[active,revision]);
 return <section className="panel"><div className="panel-heading"><h2>Cargas disponibles</h2><button className="secondary" disabled={busy||loading} onClick={()=>void load(data.pagina)}>Actualizar cargas</button></div>
 <p>Abre una carga anterior de tu usuario. El administrador también puede consultar las de otros usuarios.</p>
 {error&&<p role="alert" className="error-box">{error}</p>}{!data.total&&!loading&&<p>No tienes cargas disponibles.</p>}
 {!!data.total&&<div className="table-scroll"><table><thead><tr><th>Fecha</th><th>Usuario</th><th>Archivos</th><th>Estado</th><th>Acción</th></tr></thead><tbody>{data.datos.map(lot=>{const expired=new Date(lot.vence_en).getTime()<=Date.now();return <tr key={lot.id}><td>{new Date(lot.creado_en).toLocaleString('es-BO',{timeZone:'America/La_Paz'})}<small><code>{lot.id}</code></small></td><td>{lot.usuario??'Sin autor histórico'}</td><td>{lot.archivos}</td><td>{expired?'Vencida':lot.estado}</td><td><button className="secondary" disabled={busy||loading||expired} onClick={()=>void open(lot.id)}>Abrir carga</button></td></tr>;})}</tbody></table></div>}
 <Pager data={data} busy={busy||loading} change={p=>void load(p)}/>
 </section>;
}
