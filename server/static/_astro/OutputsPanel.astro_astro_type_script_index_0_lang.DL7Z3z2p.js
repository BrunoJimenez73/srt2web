import{a as m}from"./api.CZIbdbqf.js";import{s as u}from"./index.C_svvD_Z.js";let v=[],I=[];async function l(){try{return v=(await m("GET","api/outputs")).outputs||[],w(),v}catch(e){return console.error("Failed to fetch outputs:",e),[]}}async function h(e){try{return await m("POST","api/outputs",e),u("Salida añadida correctamente","success"),await l(),!0}catch(n){const t=n instanceof Error?n.message:String(n);return u(`Error al añadir salida: ${t}`,"error"),!1}}async function B(e){try{return await m("DELETE",`api/outputs/${e}`),u("Salida eliminada","success"),await l(),!0}catch(n){const t=n instanceof Error?n.message:String(n);return u(`Error al eliminar: ${t}`,"error"),!1}}async function $(e,n){try{return await m("POST",`api/outputs/${e}/toggle`,{enabled:n}),await l(),!0}catch(t){const s=t instanceof Error?t.message:String(t);return u(`Error: ${s}`,"error"),!1}}function w(){I.forEach(e=>e(v))}function _(e){return{web:"🌐",recording:"⏺",srt:"📡",rtmp:"📺",file:"📁",hls:"🌐"}[e]||"📤"}const k=_;let y=[];const r=new Set;function S(e){return{web:"HLS",recording:"REC",srt:"SRT",rtmp:"RTMP",file:"FILE"}[e]||e.toUpperCase()}function c(e){y=e;const n=document.getElementById("outputs-grid"),t=document.getElementById("outputs-empty"),s=document.getElementById("output-count");if(n){if(s&&(s.textContent=String(e.length)),e.length===0){t&&(t.style.display="flex"),n.querySelectorAll(".output-card").forEach(a=>a.remove());return}t&&(t.style.display="none"),n.querySelectorAll(".output-card").forEach(a=>a.remove()),e.forEach(a=>{const o=document.createElement("div");o.className=`output-card${a.state==="running"?" active":""}`,o.dataset.name=a.name;const i=r.has(a.name);let d="";a.stream_info&&(d=Object.entries(a.stream_info).slice(0,4).map(([g,b])=>`<div class="detail-item"><span class="detail-label">${g}</span><span class="detail-value">${b}</span></div>`).join("")),o.innerHTML=`
        <div class="output-card ${a.state==="running"?"active":""}">
          <div class="process-header" data-card-toggle="${a.name}">
            <span class="process-indicator ${a.state==="running"?"active":""}"></span>
            <span class="process-title">${k(a.type)} ${a.name}</span>
            <span class="output-type-badge">${S(a.type)}</span>
            <label class="toggle-switch">
              <input type="checkbox" ${a.enabled?"checked":""} data-output-toggle="${a.name}" />
              <span class="toggle-slider"></span>
            </label>
          </div>
          <div class="process-content">
            <div class="output-stats">
              <div class="stat-item">
                <span class="stat-label">Chunks</span>
                <span class="stat-value">${a.processed_chunks}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Estado</span>
                <span class="stat-value ${a.state==="running"?"success":a.state==="error"?"error":""}">${a.state}</span>
              </div>
            </div>
            <div class="metrics-row">
              <div class="metric-mini">
                <span class="metric-label">Tiempo</span>
                <span class="metric-value">${a.last_process_time_ms}ms</span>
              </div>
              <div class="metric-mini">
                <span class="metric-label">Tipo</span>
                <span class="metric-value">${a.type}</span>
              </div>
              <div class="metric-mini">
                <span class="metric-label">Activo</span>
                <span class="metric-value">${a.enabled?"✓":"✗"}</span>
              </div>
            </div>
            ${a.error?`<div class="error-box"><span class="error-label">Error:</span><span class="error-msg">${a.error}</span></div>`:""}
            <div class="output-details">
              ${d||'<div class="detail-item"><span class="detail-label">Sin stream info</span><span class="detail-value">-</span></div>'}
            </div>
            <div class="output-actions">
              <button class="btn-expand ${i?"expanded":""}" data-expand="${a.name}" title="Configuración">▼ Más</button>
              <button class="btn-remove" data-output-remove="${a.name}" title="Eliminar">🗑️ Eliminar</button>
            </div>
          </div>
        </div>
      `,n.appendChild(o)}),L()}}function L(){document.querySelectorAll("[data-output-toggle]").forEach(e=>{e.addEventListener("change",async n=>{const t=n.target.dataset.outputToggle,s=n.target.checked;t&&await $(t,s)})}),document.querySelectorAll("[data-output-remove]").forEach(e=>{e.addEventListener("click",async n=>{const t=n.target.dataset.outputRemove;t&&confirm(`¿Eliminar salida "${t}"?`)&&await B(t)})}),document.querySelectorAll("[data-expand]").forEach(e=>{e.addEventListener("click",n=>{n.stopPropagation();const t=n.target.dataset.expand;t&&(r.has(t)?r.delete(t):r.add(t),c(y))})}),document.querySelectorAll("[data-card-toggle]").forEach(e=>{e.addEventListener("click",n=>{const t=n.currentTarget.dataset.cardToggle;t&&(r.has(t)?r.delete(t):r.add(t),c(y))})})}function f(){const e=document.getElementById("output-form-wrapper");e&&(e.style.display="flex")}function p(){const e=document.getElementById("output-form-wrapper");e&&(e.style.display="none")}function E(e){document.querySelectorAll(".output-type-settings").forEach(g=>{g.style.display="none"});const n=document.getElementById(`settings-${e}`);n&&(n.style.display="block");const t=document.getElementById("output-recording-quality"),s=document.getElementById("recording-bitrate-label"),a=document.getElementById("output-recording-bitrate");t&&s&&a&&(t.value==="crf"?(s.textContent="CRF (18-28)",a.value="23"):(s.textContent="Bitrate (kbps)",a.value="5000"));const o=document.getElementById("output-recording-split"),i=document.getElementById("recording-split-value-group"),d=document.getElementById("recording-split-label");o&&i&&d&&(o.value==="none"?i.style.display="none":(i.style.display="block",d.textContent=o.value==="time"?"Minutos":"MB"))}async function x(){const e=document.getElementById("new-output-type")?.value||"web",n=Date.now(),t=`${e}_${n}`;let s={type:e,name:t};if(e==="web")s={...s,segment_duration:parseInt(document.getElementById("output-web-segment")?.value||"4"),list_size:parseInt(document.getElementById("output-web-list")?.value||"6"),audio_offset_ms:0,encoder_mode:"auto"};else if(e==="recording"){const o=document.getElementById("output-recording-quality")?.value||"cbr";s={...s,output_path:document.getElementById("output-recording-path")?.value||"./output/recording.mp4",format:document.getElementById("output-recording-format")?.value||"mp4",codec:document.getElementById("output-recording-codec")?.value||"copy",quality_mode:o,video_bitrate:o==="cbr"?document.getElementById("output-recording-bitrate")?.value+"k":void 0,video_crf:o==="crf"?parseInt(document.getElementById("output-recording-bitrate")?.value||"23"):void 0,audio_codec:"aac",split_mode:document.getElementById("output-recording-split")?.value||"none",split_value:document.getElementById("output-recording-split-value")?.value?parseInt(document.getElementById("output-recording-split-value").value):void 0,subtitles:document.getElementById("output-recording-subs")?.value||"none"}}else e==="srt"?s={...s,url:document.getElementById("output-srt-url")?.value||"srt://localhost:9001",mode:document.getElementById("output-srt-mode")?.value||"caller",latency_ms:parseInt(document.getElementById("output-srt-latency")?.value||"2000"),video_bitrate:document.getElementById("output-srt-vbitrate")?.value||"2500k",audio_bitrate:document.getElementById("output-srt-abitrate")?.value||"128k"}:e==="rtmp"&&(s={...s,url:document.getElementById("output-rtmp-url")?.value||"rtmp://localhost/live/stream",video_bitrate:document.getElementById("output-rtmp-vbitrate")?.value||"2500k",audio_bitrate:document.getElementById("output-rtmp-abitrate")?.value||"128k",encoder_mode:"auto"});if(await h({name:t,type:e,config:s})){p();const o=await l();c(o)}}document.getElementById("btn-add-output")?.addEventListener("click",f);document.getElementById("btn-add-first-output")?.addEventListener("click",f);document.getElementById("btn-close-output-form")?.addEventListener("click",p);document.getElementById("output-form-backdrop")?.addEventListener("click",p);document.getElementById("btn-cancel-output")?.addEventListener("click",p);document.getElementById("btn-save-output")?.addEventListener("click",x);document.getElementById("new-output-type")?.addEventListener("change",e=>{E(e.target.value)});document.getElementById("output-recording-quality")?.addEventListener("change",()=>{E("recording")});document.getElementById("output-recording-split")?.addEventListener("change",()=>{E("recording")});l().then(c).catch(()=>c([]));window.refreshOutputs=async()=>{const e=await l();c(e)};
