/** Simple reactive-ish state store */
const state={snapshot:null,liveArticles:null,intelligenceGraph:null,intelligenceBrain:null,intelligenceBrief:null,sources:null,sourceHealth:null,markets:null,mapData:null,mapPoints:null,whatChanged:null,eventHistory:null,historicalTrends:null,liveStatus:null,refreshManifest:null,validationResults:null,pipelineHistory:null,lastSuccessfulFetch:null,status:'loading',errors:{},feedMeta:{}};
const listeners=new Set();
export function getState(){return {...state};}
export function setState(partial){Object.assign(state,partial);listeners.forEach(fn=>fn(getState()));}
export function subscribe(fn){listeners.add(fn);return()=>listeners.delete(fn);}
export function setError(key,message){state.errors[key]=message;setState({errors:{...state.errors}});}
export function clearError(key){delete state.errors[key];setState({errors:{...state.errors}});}
