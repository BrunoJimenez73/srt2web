import{a as d}from"./api.CUNSBO6C.js";import{s as o}from"./index.BpSbb1Lw.js";let l=[],f=[];async function r(){try{return l=(await d("GET","api/outputs")).outputs||[],b(),l}catch(e){return console.error("Failed to fetch outputs:",e),[]}}async function v(e){try{return await d("POST","api/outputs",e),o("Salida añadida correctamente","success"),await r(),!0}catch(t){const a=t instanceof Error?t.message:String(t);return o(`Error al añadir salida: ${a}`,"error"),!1}}async function y(e){try{return await d("DELETE",`api/outputs/${encodeURIComponent(e)}`),o("Salida eliminada","success"),await r(),!0}catch(t){const a=t instanceof Error?t.message:String(t);return o(`Error al eliminar: ${a}`,"error"),!1}}async function E(e,t){try{return await d("POST",`api/outputs/${encodeURIComponent(e)}/toggle`,{enabled:t}),await r(),!0}catch(a){const n=a instanceof Error?a.message:String(a);return o(`Error: ${n}`,"error"),!1}}function b(){f.forEach(e=>e(l))}function h(e){return{web:"🌐",recording:"⏺",srt:"📡",rtmp:"📺",file:"📁",hls:"🌐"}[e]||"📤"}function I(e){return{web:"HLS",recording:"REC",srt:"SRT",rtmp:"RTMP",file:"FILE",hls:"HLS"}[e]||e.toUpperCase()}let c=[];const u=new Set;function i(){const e=document.getElementById("outputs-list");if(e){if(e.innerHTML="",c.length===0){e.innerHTML='<div class="output-empty">Sin salidas configuradas</div>';return}c.forEach(t=>{const a=u.has(t.name),n=document.createElement("div");n.className=`output-item${t.state==="running"?" active":""}`;let s="";t.stream_info&&(s=`
          <div class="output-details">
            ${Object.entries(t.stream_info).slice(0,6).map(([m,g])=>`
              <div class="output-detail">
                <span class="output-detail-label">${m}</span>
                <span class="output-detail-value">${g}</span>
              </div>
            `).join("")}
          </div>
        `),n.innerHTML=`
        <div class="output-item-header" data-output-header="${t.name}">
          <span class="output-collapse-icon${a?" expanded":""}">▶</span>
          <span class="output-item-title">${h(t.type)} ${t.name}</span>
          <span class="output-type-badge">${I(t.type)}</span>
          <label class="output-card-toggle" data-output-toggle-label="${t.name}">
            <input type="checkbox" ${t.enabled?"checked":""} data-output-toggle="${t.name}" />
            <span class="toggle-slider${t.enabled?" on":""}"></span>
          </label>
        </div>
        <div class="output-item-body${a?" expanded":""}" data-output-body="${t.name}">
          <div class="output-stats">
            <div class="output-stat">
              <span class="output-stat-label">Chunks</span>
              <span class="output-stat-value">${t.processed_chunks}</span>
            </div>
            <div class="output-stat">
              <span class="output-stat-label">Estado</span>
              <span class="output-stat-value ${t.state==="running"?"success":t.state==="error"?"error":""}">${t.state}</span>
            </div>
          </div>
          ${t.error?`<div class="output-stat-value error" style="padding: 8px; margin-bottom: 8px;">${t.error}</div>`:""}
          ${s}
          <div class="output-item-actions">
            <button class="btn-remove-output" data-output-remove="${t.name}">🗑️ Eliminar</button>
          </div>
        </div>
      `,e.appendChild(n)}),$()}}function $(){document.querySelectorAll("[data-output-header]").forEach(e=>{e.addEventListener("click",t=>{const a=t.currentTarget.dataset.outputHeader;if(a){const n=document.querySelector(`[data-output-body="${a}"]`),s=t.currentTarget.querySelector(".output-collapse-icon");u.has(a)?(u.delete(a),n?.classList.remove("expanded"),s?.classList.remove("expanded")):(u.add(a),n?.classList.add("expanded"),s?.classList.add("expanded"))}})}),document.querySelectorAll("[data-output-toggle]").forEach(e=>{e.addEventListener("change",async t=>{const a=t.target.dataset.outputToggle,n=t.target.checked;a&&await E(a,n)})}),document.querySelectorAll("[data-output-toggle-label]").forEach(e=>{e.addEventListener("click",t=>{t.stopPropagation()})}),document.querySelectorAll("[data-output-remove]").forEach(e=>{e.addEventListener("click",async t=>{const a=t.target.dataset.outputRemove;a&&await showDeleteConfirm(a)&&await y(a)})})}function p(){const e=document.getElementById("btn-add-output-toggle"),t=document.getElementById("add-output-form"),a=e?.querySelector(".add-icon");t&&t.classList.toggle("expanded"),a&&a.classList.toggle("expanded"),t?.classList.contains("expanded")?t.style.display="flex":t&&(t.style.display="none")}function w(e){document.querySelectorAll(".output-type-settings").forEach(a=>{a.style.display="none"});const t=document.getElementById(`settings-${e}`);t&&(t.style.display="flex")}async function B(){const e=document.getElementById("new-output-type")?.value||"web",t=Date.now(),a=`${e}_${t}`;let n={type:e,name:a};e==="web"?n=Object.assign({},n,{segment_duration:parseInt(document.getElementById("output-web-segment")?.value||"4"),list_size:parseInt(document.getElementById("output-web-list")?.value||"6"),audio_offset_ms:0,encoder_mode:"auto"}):e==="recording"?n=Object.assign({},n,{output_path:document.getElementById("output-recording-path")?.value||"./output/recording.mp4",format:document.getElementById("output-recording-format")?.value||"mp4",codec:"aac",audio_codec:"aac"}):e==="srt"?n=Object.assign({},n,{url:document.getElementById("output-srt-url")?.value||"srt://localhost:9001",mode:document.getElementById("output-srt-mode")?.value||"caller",latency_ms:parseInt(document.getElementById("output-srt-latency")?.value||"2000"),video_bitrate:document.getElementById("output-srt-vbitrate")?.value||"2500k",audio_bitrate:document.getElementById("output-srt-abitrate")?.value||"128k"}):e==="rtmp"?n=Object.assign({},n,{url:document.getElementById("output-rtmp-url")?.value||"rtmp://localhost/live/stream",video_bitrate:document.getElementById("output-rtmp-vbitrate")?.value||"2500k",audio_bitrate:document.getElementById("output-rtmp-abitrate")?.value||"128k",encoder_mode:"auto"}):e==="file"&&(n=Object.assign({},n,{output_path:document.getElementById("output-file-path")?.value||"./output",save_video:document.getElementById("output-file-video")?.value==="true",save_audio:document.getElementById("output-file-audio")?.value==="true",save_subs:document.getElementById("output-file-subs")?.value==="true"})),await v({name:a,type:e,config:n})&&(u.add(a),p())}document.getElementById("btn-add-output-toggle")?.addEventListener("click",p);document.getElementById("btn-create-output")?.addEventListener("click",B);document.getElementById("new-output-type")?.addEventListener("change",e=>{w(e.target.value)});c=await r().catch(()=>[]);i();setInterval(async()=>{c=await r().catch(()=>[]),i()},5e3);
