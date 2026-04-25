function r(t){const o=Math.floor(t/60),a=Math.floor(t%60);return`${o}:${a.toString().padStart(2,"0")}`}function n(t){return new Date(t).toLocaleTimeString("en-US",{hour12:!1})}export{r as a,n as f};
