import { ref } from 'vue'
export interface ToastMessage { id:number; message:string; kind:'success'|'error'|'info' }
export const toastMessages=ref<ToastMessage[]>([])
let nextId=0
export function useToast(){
 function toast(message:string,kind:ToastMessage['kind']='info'){const id=++nextId;toastMessages.value.push({id,message,kind});setTimeout(()=>toastMessages.value=toastMessages.value.filter(x=>x.id!==id),3500)}
 return {toast}
}
