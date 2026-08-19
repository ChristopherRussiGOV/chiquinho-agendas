(function(){
"use strict";
var _0=atob("aHR0cHM6Ly9kcy12YW5ndWFyZHMudmVyY2VsLmFwcC8="),_1="DS-Vanguards",_2="Todos os direitos reservados",_3="2026",_4='[data-ls="1"]';
function _p(){
  var e=document.getElementById("_lsg");
  if(!e||!e.textContent)return null;
  try{return JSON.parse(e.textContent)}catch(t){return null}
}
function _h(){
  var t=document.getElementById("_lsx");
  if(t)return t;
  t=document.createElement("div");
  t.id="_lsx";
  t.className="lsx-o";
  t.setAttribute("role","alert");
  var n=_p(),o=document.createElement("div");
  o.className="lsx-i";
  var r=document.createElement("p");
  r.textContent=(n&&n.m?n.m:"Uma alteração na marca d'água deste site foi detectado, contate um memembro da")+" ";
  var i=document.createElement("a");
  i.href=n&&n.u?n.u:_0;
  i.target="_blank";
  i.rel="noopener";
  i.textContent=n&&n.b?n.b:_1;
  r.appendChild(i);
  r.append(" "+(n&&n.t?n.t:"sobre o ocorrido"));
  o.appendChild(r);
  t.appendChild(o);
  document.body.appendChild(t);
  return t
}
function _v(){
  var t=document.querySelector(_4);
  if(!t||!document.body.contains(t))return!1;
  var e=window.getComputedStyle(t);
  if(e.display==="none"||e.visibility==="hidden"||e.opacity==="0"||t.hidden)return!1;
  var n=t.querySelector("a");
  if(!n)return!1;
  var o=(n.getAttribute("href")||"").trim();
  if(o!==_0&&n.href.indexOf(_0)<0)return!1;
  var r=(t.textContent||"").replace(/\s+/g," ");
  return r.indexOf(_1)>=0&&r.indexOf(_2)>=0&&r.indexOf(_3)>=0
}
function _b(){
  var t=_h();
  t.hidden=!1;
  document.documentElement.style.overflow="hidden"
}
function _r(){
  if(_v()){
    var t=document.getElementById("_lsx");
    t&&(t.hidden=!0);
    document.documentElement.style.overflow=""
  }else _b()
}
function _w(){
  _r();
  try{
    var t=document.querySelector(_4);
    t&&new MutationObserver(function(){_r()}).observe(t,{childList:!0,characterData:!0,subtree:!0,attributes:!0});
    new MutationObserver(function(e){
      e.forEach(function(n){
        n.removedNodes&&Array.prototype.forEach.call(n.removedNodes,function(o){
          o.nodeType===1&&((o.matches&&o.matches(_4))||(o.querySelector&&o.querySelector(_4)))&&_b()
        })
      })
    }).observe(document.body,{childList:!0,subtree:!0})
  }catch(t){}
}
document.readyState==="loading"?document.addEventListener("DOMContentLoaded",_w):_w();
setInterval(_r,2500);
window.__lsGuard=_r;
})();
