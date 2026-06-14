var PL=[], OLU=[], DEFU=[], TMS=[], UNIT_YEARS=[], ERAS=["1999–2009","2010s","2020s"];
var IDX={byPosTeam:{},teamsByPos:{},olByYear:{},defByYear:{}};
var DATA_CACHE='nfl-170-cache-v1';

/* Uniform random selection + Elo win probability (all spins use valid-pool math). */
function randFloat(){return Math.random();}
function randInt(n){return n<=0?0:Math.floor(randFloat()*n);}
function pickUniform(arr){return arr.length?arr[randInt(arr.length)]:null;}
function shuffle(arr){
  var a=arr.slice();
  for(var i=a.length-1;i>0;i--){
    var j=randInt(i+1), tmp=a[i];a[i]=a[j];a[j]=tmp;
  }
  return a;
}
function winProbability(mine,opp){
  return Math.max(0.10,Math.min(0.93,1/(1+Math.pow(10,(opp-mine)/15))));
}

function buildIndices(){
  IDX.byPosTeam={};IDX.teamsByPos={};IDX.olByYear={};IDX.defByYear={};
  PL.forEach(function(p){
    var pos=p[2], team=canonicalTeam(p[3]);
    if(!IDX.byPosTeam[pos])IDX.byPosTeam[pos]={};
    if(!IDX.byPosTeam[pos][team])IDX.byPosTeam[pos][team]=[];
    IDX.byPosTeam[pos][team].push(p);
    if(!IDX.teamsByPos[pos])IDX.teamsByPos[pos]={};
    IDX.teamsByPos[pos][team]=true;
  });
  OLU.forEach(function(u){
    var y=u[3];if(!IDX.olByYear[y])IDX.olByYear[y]=[];IDX.olByYear[y].push(u);
  });
  DEFU.forEach(function(d){
    var y=d[3];if(!IDX.defByYear[y])IDX.defByYear[y]=[];IDX.defByYear[y].push(d);
  });
}
function setLoading(msg,sub){
  var m=document.getElementById('loading-msg'), s=document.getElementById('loading-sub');
  if(m&&msg)m.textContent=msg;
  if(s&&sub)s.textContent=sub;
}
function parseDataPayload(text){return JSON.parse(text);}
async function loadGameData(){
  var cachedKey=null;
  try{cachedKey=localStorage.getItem(DATA_CACHE+'-key');}catch(e){}
  if(cachedKey&&'caches' in window){
    try{
      var cache=await caches.open(DATA_CACHE);
      var hit=await cache.match('/nfl-data/'+cachedKey);
      if(hit){
        setLoading('Loading NFL data…','Using cached rosters');
        return parseDataPayload(await hit.text());
      }
    }catch(e){}
  }
  var sources=[{url:'nfl_data.json.gz',gzip:true,label:'compressed roster file'},{url:'nfl_data.json',gzip:false,label:'roster file'}];
  var lastErr=null;
  for(var i=0;i<sources.length;i++){
    try{
      setLoading('Loading NFL data…','Fetching '+sources[i].label);
      var res=await fetch(sources[i].url,{cache:'default'});
      if(!res.ok)throw new Error('HTTP '+res.status);
      var data;
      if(sources[i].gzip&&typeof DecompressionStream!=='undefined'){
        setLoading('Loading NFL data…','Decompressing rosters');
        var ds=new DecompressionStream('gzip');
        var stream=res.body.pipeThrough(ds);
        data=parseDataPayload(await new Response(stream).text());
      }else{
        data=parseDataPayload(await res.text());
      }
      var key=(data.meta&&data.meta.cache_key)||String((data.players||[]).length);
      try{
        localStorage.setItem(DATA_CACHE+'-key',key);
        if('caches' in window){
          var cache=await caches.open(DATA_CACHE);
          await cache.put('/nfl-data/'+key,new Response(JSON.stringify(data),{headers:{'Content-Type':'application/json'}}));
        }
      }catch(e){}
      return data;
    }catch(err){lastErr=err;}
  }
  throw lastErr||new Error('Unable to load NFL data');
}
var FRANCHISE_ALIAS={
  "St. Louis Rams":"Los Angeles Rams","STL Rams":"Los Angeles Rams",
  "San Diego Chargers":"Los Angeles Chargers","SD Chargers":"Los Angeles Chargers",
  "Oakland Raiders":"Las Vegas Raiders","OAK Raiders":"Las Vegas Raiders",
  "Los Angeles Raiders":"Las Vegas Raiders","LA Raiders":"Las Vegas Raiders"
};
function canonicalTeam(team){return FRANCHISE_ALIAS[team]||team;}
var TEAM_ABBR={
  "Arizona Cardinals":"ARI","Atlanta Falcons":"ATL","Baltimore Ravens":"BAL","Buffalo Bills":"BUF",
  "Carolina Panthers":"CAR","Chicago Bears":"CHI","Cincinnati Bengals":"CIN","Cleveland Browns":"CLE",
  "Dallas Cowboys":"DAL","Denver Broncos":"DEN","Detroit Lions":"DET","Green Bay Packers":"GB",
  "Houston Texans":"HOU","Indianapolis Colts":"IND","Jacksonville Jaguars":"JAX","Kansas City Chiefs":"KC",
  "Miami Dolphins":"MIA","Minnesota Vikings":"MIN","New England Patriots":"NE","New Orleans Saints":"NO",
  "New York Giants":"NYG","New York Jets":"NYJ","Las Vegas Raiders":"LV","Philadelphia Eagles":"PHI",
  "Pittsburgh Steelers":"PIT","Los Angeles Chargers":"LAC","San Francisco 49ers":"SF","Seattle Seahawks":"SEA",
  "Los Angeles Rams":"LAR","Tampa Bay Buccaneers":"TB","Tennessee Titans":"TEN","Washington Commanders":"WAS"
};
function teamAbbr(team){return TEAM_ABBR[canonicalTeam(team)]||canonicalTeam(team).split(' ').pop().substring(0,3).toUpperCase();}
function fmtNum(n){if(n==null||n==='—')return '—';var s=String(n).replace(/,/g,'');return isNaN(s)?n:Number(s).toLocaleString();}
function canonicalUnitName(name){
  return String(name||'')
    .replace(/St\. Louis Rams/g,'Los Angeles Rams').replace(/STL Rams/g,'Los Angeles Rams')
    .replace(/San Diego Chargers/g,'Los Angeles Chargers').replace(/SD Chargers/g,'Los Angeles Chargers')
    .replace(/Oakland Raiders/g,'Las Vegas Raiders').replace(/OAK Raiders/g,'Las Vegas Raiders')
    .replace(/Los Angeles Raiders/g,'Las Vegas Raiders').replace(/LA Raiders/g,'Las Vegas Raiders');
}
function normalizeFranchiseData(){
  if(Array.isArray(PL))PL.forEach(function(p){p[3]=canonicalTeam(p[3]);p[6]=cleanRSStat(p[6]);});
  if(Array.isArray(OLU))OLU.forEach(function(u){u[0]=canonicalUnitName(u[0]);u[1]=canonicalTeam(u[1]);u[5]=cleanRSStat(u[5]);});
  if(Array.isArray(DEFU))DEFU.forEach(function(d){d[0]=canonicalUnitName(d[0]);d[1]=canonicalTeam(d[1]);d[6]=cleanRSStat(d[6]);});
}

var DO_OFF=[
  {sl:"QB",p:"QB",l:"Quarterback",ph:"off"},
  {sl:"RB1",p:"RB",l:"Running Back",ph:"off"},
  {sl:"WR1",p:"WR",l:"Wide Receiver #1",ph:"off"},
  {sl:"WR2",p:"WR",l:"Wide Receiver #2",ph:"off"},
  {sl:"WR3",p:"WR",l:"Wide Receiver #3",ph:"off"},
  {sl:"TE",p:"TE",l:"Tight End",ph:"off"},
  {sl:"OL",p:"OL",l:"Best Statistical OL Unit",ph:"off"}
];

function eraLabel(e){return e==='2000s'?'1999–2009':e;}
function eraMatches(sourceEra,targetEra){return eraLabel(sourceEra)===eraLabel(targetEra);}
function eraFromYear(y){y=parseInt(y,10);if(y<2010)return '1999–2009';if(y<2020)return '2010s';return '2020s';}
function yearsForEra(e){return UNIT_YEARS.filter(function(y){return eraMatches(eraFromYear(y),e);});}
function playerYears(pl){
  if(Array.isArray(pl[7])&&pl[7].length)return pl[7].slice();
  var text=String(pl[6]||''), years={}, range=/\b(19\d{2}|20\d{2})[–-](\d{2}|\d{4})\b/g, m;
  while((m=range.exec(text))){
    var start=parseInt(m[1],10), end=parseInt(m[2],10);
    if(end<100)end=Math.floor(start/100)*100+end;
    for(var y=start;y<=end;y++)if(y>=1999&&y<=2025)years[y]=true;
  }
  var singles=text.match(/\b(?:19|20)\d{2}\b/g)||[];
  singles.forEach(function(y){y=parseInt(y,10);if(y>=1999&&y<=2025)years[y]=true;});
  var out=Object.keys(years).map(Number).filter(function(y){return eraMatches(eraFromYear(y),pl[4]);});
  return out.length?out:yearsForEra(pl[4]);
}
function playerOnTeamYear(pl,team,year){
  return canonicalTeam(pl[3])===canonicalTeam(team)&&playerYears(pl).indexOf(parseInt(year,10))!==-1;
}
function playerOnTeam(pl,team){
  return canonicalTeam(pl[3])===canonicalTeam(team);
}
function primaryYear(pl){
  var yrs=playerYears(pl);
  return yrs.length?yrs[yrs.length-1]:null;
}
function yearsLabel(pl){
  var yrs=playerYears(pl).slice().sort(function(a,b){return a-b;});
  if(!yrs.length)return '';
  if(yrs.length===1)return String(yrs[0]);
  return yrs[0]+'–'+yrs[yrs.length-1];
}
function isTeamPick(){
  if(!G.DO||G.idx>=G.DO.length)return false;
  var p=G.DO[G.idx].p;
  return p!=='OL'&&p!=='DEF';
}

// 17 regular-season games (18 weeks with a bye), 1999–2025 era opponents
var RSG=[
  {o:"2013 Seattle Seahawks",r:88},{o:"2019 San Francisco 49ers",r:87},
  {o:"2007 New England Patriots",r:91},{o:"2006 Los Angeles Chargers",r:85},
  {o:"2012 San Francisco 49ers",r:86},{o:"2015 Carolina Panthers",r:86},
  {o:"2009 Indianapolis Colts",r:86},{o:"2022 Philadelphia Eagles",r:88},
  {o:"2009 New Orleans Saints",r:85},{o:"2004 Pittsburgh Steelers",r:86},
  {o:"2016 Dallas Cowboys",r:84},{o:"2023 Kansas City Chiefs",r:89},
  {o:"2021 Tampa Bay Buccaneers",r:85},{o:"2014 Denver Broncos",r:86},
  {o:"2011 Green Bay Packers",r:87},{o:"2002 Tampa Bay Buccaneers",r:85},
  {o:"2024 Detroit Lions",r:86}
];
var BYE_AFTER=8;

var G={idx:0,roster:{},used:new Set(),spinning:false,games:[],tr:0,spinTeam:'',spinEra:'',scheme:'',DO:[],stage:'offense'};

function showScr(id){
  ["S0","Ssch","S1","S2","S3"].forEach(function(s){document.getElementById(s).classList.remove('on');});
  document.getElementById(id).classList.add('on');
}
function calcTR(){
  var v=[];Object.keys(G.roster).forEach(function(k){var p=G.roster[k];if(p&&p.r)v.push(p.r);});
  if(!v.length)return 0;
  return Math.round(v.reduce(function(a,b){return a+b;},0)/v.length);
}
function gc(r){
  if(r>=97)return{g:"S+",c:"#6b7280"};if(r>=95)return{g:"S",c:"#6b7280"};
  if(r>=93)return{g:"A+",c:"#4ade80"};if(r>=91)return{g:"A",c:"#4ade80"};
  if(r>=89)return{g:"B+",c:"#60a5fa"};if(r>=87)return{g:"B",c:"#60a5fa"};
  return{g:"C",c:"#94a3b8"};
}
function isYearUnitPick(){
  if(!G.DO||G.idx>=G.DO.length)return false;
  var p=G.DO[G.idx].p;
  return p==='OL'||p==='DEF';
}
function selectScheme(s){
  G.scheme=s;G.stage='defense';G.idx=0;
  G.DO=[{sl:"DEF",p:"DEF",l:"Team Defense Unit",ph:"def"}];
  document.getElementById('schm-lbl').textContent=s==='43'?'4-3':'3-4';
  document.getElementById('def-sh').textContent='DEPTH CHART';
  showScr('S1');refreshDraft();
}
function startDraft(){
  G={idx:0,roster:{},used:new Set(),spinning:false,games:[],tr:0,spinTeam:'',spinEra:'',scheme:'',DO:DO_OFF.slice(),stage:'offense'};
  document.getElementById('schm-lbl').textContent='OFFENSE';
  document.getElementById('def-sh').textContent='OFFENSE DEPTH CHART';
  showScr('S1');refreshDraft();
}

function refreshDraft(){
  var pick=G.DO[G.idx];
  document.getElementById('pkl').textContent='PICK '+(G.idx+1)+' / '+G.DO.length;
  document.getElementById('pnl').textContent=pick.l;
  var sub=document.getElementById('pick-sub');
  if(sub)sub.textContent=G.stage==='offense'?'Offense draft · team spin per position':'Defense draft · year spin · top 3 units';
  var t=calcTR();document.getElementById('trl').textContent=t>0?'OVR '+t:'—';
  var pl=document.getElementById('phase-lbl');
  pl.className='dphase '+pick.ph;
  pl.textContent=pick.ph==='off'?'OFFENSE':(G.scheme==='43'?'4-3 TEAM DEFENSE':'3-4 TEAM DEFENSE');
  var pb=document.getElementById('prog');pb.innerHTML='';
  for(var i=0;i<G.DO.length;i++){
    var d=document.createElement('div');
    d.className='pip'+(i<G.idx?' dn':'')+(i===G.idx?' cr':'');
    pb.appendChild(d);
  }
  var mode=isYearUnitPick(), teamPick=isTeamPick();
  var eraCard=document.getElementById('rte');
  var teamCard=document.getElementById('rde');
  var eraFoot=document.getElementById('era-foot-lbl');
  eraCard.classList.toggle('hide',teamPick);
  teamCard.classList.toggle('hide',mode);
  if(eraFoot)eraFoot.style.visibility=(teamPick||mode)?'hidden':'visible';
  var teamFoot=document.querySelector('.spin-card-foot span:first-child');
  if(teamFoot)teamFoot.style.visibility=mode?'hidden':'visible';
  document.getElementById('rrteam').style.display='';
  document.getElementById('rrteam').textContent=teamPick?'↩ New Team':(mode?'↩ New Year':'↩ New Year');
  document.getElementById('rrera').style.display=(mode||teamPick)?'none':'';
  document.getElementById('rrera').textContent='↩ New Year';
  document.getElementById('spbtn').textContent=mode?'SPIN YEAR':(teamPick?'SPIN TEAM':'SPIN');
  document.getElementById('rvt').textContent='???';document.getElementById('rvd').textContent='???';
  ['rvt','rvd'].forEach(function(id){document.getElementById(id).classList.remove('bl');});
  ['rte','rde'].forEach(function(id){document.getElementById(id).classList.remove('sp');});
  document.getElementById('spbtn').disabled=false;
  document.getElementById('opts').style.display='none';
  document.getElementById('rrrow').style.display='none';
  G.spinning=false;G.spinTeam='';G.spinEra='';
  renderClip();
}

function spinReel(el,valEl,pool,onDone,ticks,forcedResult,fmt){
  if(!pool.length){if(onDone)onDone(null);return;}
  fmt=fmt||function(x){return x;};
  el.classList.add('sp');valEl.classList.add('bl');
  var c=0,tot=ticks||22;
  var target=forcedResult==null?pickUniform(pool):forcedResult;
  var iv=setInterval(function(){
    c++;valEl.textContent=fmt(pool[randInt(pool.length)]);
    if(c>=tot){
      clearInterval(iv);
      valEl.textContent=fmt(target);valEl.classList.remove('bl');el.classList.remove('sp');
      if(onDone)onDone(target);
    }
  },80);
}
function eligibleTeams(){
  var pos=G.DO[G.idx].p, teams=[], seen=IDX.teamsByPos[pos]||{};
  Object.keys(seen).forEach(function(team){
    var list=IDX.byPosTeam[pos]&&IDX.byPosTeam[pos][team];
    if(list&&list.some(function(pl){return !G.used.has(pl[0]);}))teams.push(team);
  });
  return teams.sort();
}
function eligibleYears(){
  var pos=G.DO[G.idx].p, years=[];
  if(pos==='OL')years=Object.keys(IDX.olByYear).map(Number);
  else if(pos==='DEF')years=Object.keys(IDX.defByYear).map(Number);
  else years=UNIT_YEARS.slice();
  return years.sort(function(a,b){return a-b;});
}
function eligibleCombos(){
  var pos=G.DO[G.idx].p, seen={}, combos=[];
  PL.forEach(function(pl){
    if(pl[2]!==pos||G.used.has(pl[0]))return;
    playerYears(pl).forEach(function(year){
      var team=canonicalTeam(pl[3]), key=year+'|'+team;
      if(!seen[key]){seen[key]=true;combos.push({year:year,team:team});}
    });
  });
  return combos;
}

function doSpin(){
  if(G.spinning)return;G.spinning=true;
  document.getElementById('spbtn').disabled=true;
  document.getElementById('rrrow').style.display='none';
  document.getElementById('opts').style.display='none';
  var mode=isYearUnitPick(), teamPick=isTeamPick();
  if(mode){
    var years=eligibleYears(), target=pickUniform(years);
    if(!target){G.spinning=false;document.getElementById('spbtn').disabled=false;return;}
    spinReel(document.getElementById('rte'),document.getElementById('rvt'),years,function(y){
      G.spinTeam=y;G.spinEra=eraFromYear(y);G.spinning=false;
      document.getElementById('rrrow').style.display='flex';
      showOpts(y,G.spinEra);
    },26,target,String);
    return;
  }
  if(teamPick){
    var teams=eligibleTeams(), target=pickUniform(teams);
    if(!target){G.spinning=false;document.getElementById('spbtn').disabled=false;return;}
    spinReel(document.getElementById('rde'),document.getElementById('rvd'),teams,function(t){
      G.spinTeam=t;G.spinEra='';G.spinning=false;
      document.getElementById('rrrow').style.display='flex';
      showOpts(t);
    },22,target,teamAbbr);
    return;
  }
  var combos=eligibleCombos(), target=pickUniform(combos);
  if(!target){G.spinning=false;document.getElementById('spbtn').disabled=false;return;}
  var yd=false,td=false,fy='',ft='';
  spinReel(document.getElementById('rte'),document.getElementById('rvt'),UNIT_YEARS,function(r){fy=r;yd=true;if(td)fin(fy,ft);},26,target.year,String);
  spinReel(document.getElementById('rde'),document.getElementById('rvd'),TMS,function(r){ft=r;td=true;if(yd)fin(fy,ft);},22,target.team,teamAbbr);
  function fin(y,t){G.spinTeam=t;G.spinEra=y;G.spinning=false;document.getElementById('rrrow').style.display='flex';showOpts(t,y);}
}
function rerollTeam(){
  if(G.spinning)return;G.spinning=true;
  var mode=isYearUnitPick(), teamPick=isTeamPick();
  if(teamPick){
    var teams=eligibleTeams(), target=pickUniform(teams);
    if(!target){G.spinning=false;return;}
    spinReel(document.getElementById('rde'),document.getElementById('rvd'),teams,function(t){
      G.spinTeam=t;G.spinEra='';G.spinning=false;showOpts(t);
    },18,target,teamAbbr);
    return;
  }
  var years=eligibleYears(), target=null;
  if(mode){
    target=pickUniform(years);
    if(!target){G.spinning=false;return;}
    spinReel(document.getElementById('rte'),document.getElementById('rvt'),years,function(r){
      G.spinTeam=r;G.spinEra=eraFromYear(r);G.spinning=false;showOpts(r,G.spinEra);
    },18,target,String);
    return;
  }
  var sameTeam=eligibleCombos().filter(function(c){return c.team===G.spinTeam;});
  var pool=sameTeam.length?sameTeam:eligibleCombos();
  target=pickUniform(pool);
  if(!target){G.spinning=false;return;}
  spinReel(document.getElementById('rte'),document.getElementById('rvt'),UNIT_YEARS,function(r){
    G.spinTeam=target.team;G.spinEra=r;document.getElementById('rvd').textContent=teamAbbr(target.team);G.spinning=false;showOpts(target.team,r);
  },18,target.year,String);
}
function rerollEra(){
  if(G.spinning||isYearUnitPick()||isTeamPick())return;G.spinning=true;
  var sameYear=eligibleCombos().filter(function(c){return c.year===parseInt(G.spinEra,10);});
  var pool=sameYear.length?sameYear:eligibleCombos(), target=pickUniform(pool);
  if(!target){G.spinning=false;return;}
  var teams=eligibleTeams().length?eligibleTeams():TMS;
  spinReel(document.getElementById('rde'),document.getElementById('rvd'),teams,function(r){
    G.spinTeam=r;G.spinEra=target.year;document.getElementById('rvt').textContent=String(target.year);G.spinning=false;showOpts(r,target.year);
  },18,target.team,teamAbbr);
}

function playerOvr(pl){return parseInt(pl[5],10)||0;}
function statColumns(pos){
  var ydsLbl=pos==='QB'?'PASS':(pos==='RB'?'RUSH':'REC');
  return [{k:'ovr',l:'OVR'},{k:'yds',l:ydsLbl},{k:'td',l:'TD'},{k:'yrs',l:'YRS'},{k:'era',l:'ERA'}];
}
function extractPlayerStats(pl,pos){
  var t=cleanRSStat(pl[6]||''), yds='—', td='—', m;
  if(pos==='QB'){
    m=t.match(/([\d,]+)\s+pass yds/i);if(m)yds=m[1];
    m=t.match(/(\d+)\s+(?:pass\s+)?TD/i);if(!m)m=t.match(/(\d+)\s+TD/i);if(m)td=m[1];
  }else if(pos==='RB'){
    m=t.match(/([\d,]+)\s+rush yds/i);if(m)yds=m[1];
    m=t.match(/(\d+)\s+TD/i);if(m)td=m[1];
  }else{
    m=t.match(/([\d,]+)\s+rec yds/i);if(m)yds=m[1];
    m=t.match(/(\d+)\s+TD/i);if(m)td=m[1];
  }
  var yrs=playerYears(pl).length;
  return {ovr:playerOvr(pl),yds:yds,td:td==='—'?0:parseInt(td,10)||0,yrs:yrs,era:eraLabel(pl[4])};
}
function statSortValue(pl,pos,key){
  var st=extractPlayerStats(pl,pos);
  if(key==='ovr')return st.ovr;
  if(key==='yds')return parseInt(String(st.yds).replace(/,/g,''),10)||0;
  if(key==='td')return typeof st.td==='number'?st.td:parseInt(st.td,10)||0;
  if(key==='yrs')return st.yrs;
  return 0;
}
function sortPlayerPool(pool,pos,key){
  return pool.slice().sort(function(a,b){return statSortValue(b,pos,key)-statSortValue(a,pos,key);});
}
function browserStatCell(val,lbl,isOvr){
  var cls='browser-stat'+(isOvr?' ovr-col':'');
  return '<div class="'+cls+'"><span class="browser-stat-val">'+esc(fmtNum(val))+'</span><span class="browser-stat-lbl">'+esc(lbl)+'</span></div>';
}
function renderBrowserRows(pool,pos){
  var cols=statColumns(pos), html='';
  for(var i=0;i<pool.length;i++){
    var pl=pool[i], st=extractPlayerStats(pl,pos);
    var vals={ovr:st.ovr,yds:st.yds,td:st.td,yrs:st.yrs,era:st.era};
    html+='<div class="browser-row" data-name="'+esc(pl[1].toLowerCase())+'"><div class="browser-info">'+
      '<div class="browser-name">'+esc(pl[1])+'</div>'+
      '<div class="browser-pos">'+esc(pos)+'</div>'+
      '<div class="browser-team">'+esc(teamAbbr(pl[3]))+' · '+esc(yearsLabel(pl))+'</div></div>';
    for(var c=0;c<cols.length;c++){
      html+=browserStatCell(vals[cols[c].k],cols[c].l,cols[c].k==='ovr');
    }
    html+='</div>';
  }
  return html;
}
function positionFilterHtml(activePos){
  var pills=['QB','RB','WR','TE'], html='';
  for(var i=0;i<pills.length;i++){
    var p=pills[i];
    html+='<span class="browser-filter'+(p===activePos?' active':' inactive')+'">'+p+'</span>';
  }
  return html;
}
function mountPlayerBrowser(el,pool,pos,onPick){
  var cols=statColumns(pos), sortKey='ovr';
  var sorted=sortPlayerPool(pool,pos,sortKey);
  el.style.display='block';
  el.className='player-browser';
  el.innerHTML=
    '<div class="browser-toolbar-top">'+
      '<div class="browser-filters">'+positionFilterHtml(pos)+'</div>'+
      '<div class="browser-search-wrap"><span class="browser-search-icon">⌕</span><input class="browser-search" type="search" placeholder="Search..." autocomplete="off"></div>'+
      '<select class="browser-sort" aria-label="Sort by">'+
        '<option value="ovr" selected>OVR</option><option value="yds">YDS</option><option value="td">TD</option><option value="yrs">YRS</option>'+
      '</select>'+
    '</div>'+
    '<div class="browser-count-row"><span class="browser-count">'+sorted.length+' player'+(sorted.length===1?'':'s')+' available</span></div>'+
    '<div class="browser-head"><span>Player</span>'+
      cols.map(function(c){return '<span class="bh-stat">'+c.l+'</span>';}).join('')+
    '</div>'+
    '<div class="browser-list">'+renderBrowserRows(sorted,pos)+'</div>';
  var list=el.querySelector('.browser-list');
  var countEl=el.querySelector('.browser-count');
  var sortSel=el.querySelector('.browser-sort');
  var input=el.querySelector('.browser-search');
  var currentPool=sorted.slice();
  function bindRows(){
    list.innerHTML=renderBrowserRows(currentPool,pos);
    list.querySelectorAll('.browser-row').forEach(function(row,idx){
      row.onclick=function(){onPick(currentPool[idx],primaryYear(currentPool[idx]));};
    });
    applySearchFilter(input?input.value:'');
  }
  function applySearchFilter(q){
    q=(q||'').toLowerCase().trim();
    var shown=0;
    list.querySelectorAll('.browser-row').forEach(function(row,i){
      var match=!q||currentPool[i][1].toLowerCase().indexOf(q)!==-1;
      row.style.display=match?'':'none';
      if(match)shown++;
    });
    if(countEl)countEl.textContent=shown+' player'+(shown===1?'':'s')+' available';
  }
  if(sortSel){
    sortSel.onchange=function(){
      sortKey=sortSel.value;
      currentPool=sortPlayerPool(pool,pos,sortKey);
      bindRows();
    };
  }
  if(input){input.oninput=function(){applySearchFilter(input.value);};}
  bindRows();
}
function mountUnitBrowser(el,items,kind,onPick){
  el.style.display='block';
  el.className='player-browser';
  var labels=kind==='def'?['OVR','PTS','YDS','YRS','ERA']:['OVR','RANK','YEAR','YRS','ERA'];
  var sorted=items.slice().sort(function(a,b){return (parseInt(b[4],10)||0)-(parseInt(a[4],10)||0);});
  var rows='';
  for(var i=0;i<sorted.length;i++){
    (function(u,idx){
      var m=kind==='def'?defMetricsFromData(u,idx):null;
      var ovr=parseInt(u[4],10)||0;
      var s1=ovr, s2=kind==='def'?(m&&m.pointsAllowed!=null?m.pointsAllowed:'—'):('#'+(idx+1));
      var s3=kind==='def'?(m&&m.yardsAllowed!=null?m.yardsAllowed:u[3]):u[3];
      var sub=kind==='def'?'DEF UNIT':'OL UNIT';
      rows+=
        '<div class="browser-row" data-name="'+esc(String(u[0]).toLowerCase())+'">'+
          '<div class="browser-info">'+
            '<div class="browser-name">'+esc(canonicalUnitName(u[0]))+'</div>'+
            '<div class="browser-pos">'+sub+'</div>'+
            '<div class="browser-team">'+esc(teamAbbr(u[1]))+' · '+u[3]+'</div>'+
          '</div>'+
          browserStatCell(s1,labels[0],true)+
          browserStatCell(s2,labels[1],false)+
          browserStatCell(s3,labels[2],false)+
          browserStatCell(1,labels[3],false)+
          browserStatCell(eraLabel(u[2]),labels[4],false)+
        '</div>';
    })(sorted[i],i);
  }
  el.innerHTML=
    '<div class="browser-toolbar-top">'+
      '<div class="browser-filters"><span class="browser-filter active">'+(kind==='def'?'DEF':'OL')+'</span></div>'+
      '<div class="browser-search-wrap"><span class="browser-search-icon">⌕</span><input class="browser-search" type="search" placeholder="Search..." autocomplete="off"></div>'+
      '<select class="browser-sort" aria-label="Sort by"><option value="ovr" selected>OVR</option></select>'+
    '</div>'+
    '<div class="browser-count-row"><span class="browser-count">'+sorted.length+' unit'+(sorted.length===1?'':'s')+' available</span></div>'+
    '<div class="browser-head"><span>Unit</span>'+
      labels.map(function(l){return '<span class="bh-stat">'+l+'</span>';}).join('')+
    '</div>'+
    '<div class="browser-list">'+rows+'</div>';
  el.querySelectorAll('.browser-row').forEach(function(row,idx){
    row.onclick=function(){onPick(sorted[idx],idx);};
  });
}

function showOpts(team,year){
  try{
    var pos=G.DO[G.idx].p;
    var el=document.getElementById('opts');
    if(pos==='OL'){showUnits(team,eraFromYear(team));return;}
    if(pos==='DEF'){showDefUnits(team,eraFromYear(team));return;}
    var teamPick=isTeamPick(), pool=[], teamKey=canonicalTeam(team);
    var source=IDX.byPosTeam[pos]&&IDX.byPosTeam[pos][teamKey]?IDX.byPosTeam[pos][teamKey]:[];
    for(var i=0;i<source.length;i++){
      var pl=source[i];
      if(G.used.has(pl[0]))continue;
      if(teamPick)pool.push(pl);
      else if(playerOnTeamYear(pl,team,year))pool.push(pl);
    }
    pool.sort(function(a,b){return playerOvr(b)-playerOvr(a);});
    el.innerHTML='';
    if(!pool.length){
      el.style.display='block';
      el.className='';
      el.innerHTML='<div class="noopts">No loaded '+G.DO[G.idx].l+' options for <strong>'+esc(teamAbbr(team))+'</strong>. Use <strong>↩ New Team</strong>.</div>';
      return;
    }
    mountPlayerBrowser(el,pool,pos,function(pl,y){pickP(pl,y);});
  }catch(e){console.warn(e);}
}

function showUnits(year,era){
  try{
    var el=document.getElementById('opts');el.innerHTML='';
    year=parseInt(year,10);if(!year){year=2024;}era=eraFromYear(year);G.spinEra=era;
    var yearPool=(IDX.olByYear[year]||[]).slice().sort(function(a,b){return b[4]-a[4];}).slice(0,3);
    if(!yearPool.length){
      el.style.display='block';
      el.innerHTML='<div class="noopts">No OL-unit data for '+year+'. Use ↩ New Year.</div>';
      return;
    }
    mountUnitBrowser(el,yearPool,'ol',function(u){pickU(u);});
  }catch(e){console.warn(e);}
}

function showDefUnits(year,era){
  try{
    var el=document.getElementById('opts');el.innerHTML='';
    year=parseInt(year,10);if(!year){year=2024;}era=eraFromYear(year);G.spinEra=era;
    var yearPool=(IDX.defByYear[year]||[]).slice().sort(function(a,b){
      var aFit=a[5]===G.scheme?1:0, bFit=b[5]===G.scheme?1:0;
      if(bFit!==aFit)return bFit-aFit;
      return b[4]-a[4];
    }).slice(0,3);
    if(!yearPool.length){
      el.style.display='block';
      el.innerHTML='<div class="noopts">No defensive-unit data for '+year+'. Use ↩ New Year.</div>';
      return;
    }
    mountUnitBrowser(el,yearPool,'def',function(d,idx){
      pickD(d,defMetricsFromData(d,idx));
    });
  }catch(e){console.warn(e);}
}

function defMetricsFromData(d,idx){
  if(d.length>=10&&d[7]!=null){
    return {
      totalRank:idx+1,
      pointsAllowed:parseInt(d[7],10)||0,
      yardsAllowed:parseInt(d[8],10)||0,
      takeaways:parseInt(d[9],10)||0,
      fromData:true
    };
  }
  return defMetrics(d,'Y',idx);
}
function defMetrics(d,bucket,idx){
  // Display model for defensive units (no W/L). #1 year seed = best total/scoring D.
  var rating=parseInt(d[4]||90,10), year=parseInt(d[3]||2024,10), slot=parseInt(idx||0,10);
  var totalRank=bucket==='Y'?(slot+1):Math.max(1,Math.min(10,100-rating));
  var scoringRank=bucket==='Y'?Math.min(32,slot+1+((year+slot)%2)):Math.max(1,Math.min(12,102-rating));
  var sacks=Math.max(28,Math.min(70,Math.round(34+(rating-90)*2.2+((year+slot)%6))));
  var ints=Math.max(9,Math.min(31,Math.round(12+(rating-90)*1.05+((year+slot)%5))));
  var defTd=Math.max(1,Math.min(9,Math.round(2+(rating-90)/3+((year+slot)%3===0?1:0))));
  var takeaways=Math.max(ints,Math.min(44,ints+Math.round(10+(rating-90)*.55+((year+slot)%6))));
  return {totalRank:totalRank,scoringRank:scoringRank,sacks:sacks,ints:ints,defTd:defTd,takeaways:takeaways};
}
function defStatsHtml(m){
  if(m.fromData){
    return '<div class="def-stat-grid">'+
      '<div class="def-stat"><div class="def-stat-label">Year Rank</div><div class="def-stat-value">#'+m.totalRank+'</div></div>'+
      '<div class="def-stat"><div class="def-stat-label">Pts Allowed</div><div class="def-stat-value">'+m.pointsAllowed+'</div></div>'+
      '<div class="def-stat"><div class="def-stat-label">Yds Allowed</div><div class="def-stat-value">'+m.yardsAllowed+'</div></div>'+
      '<div class="def-stat"><div class="def-stat-label">Takeaways</div><div class="def-stat-value">'+m.takeaways+'</div></div>'+
    '</div>';
  }
  return '<div class="def-stat-grid">'+
    '<div class="def-stat"><div class="def-stat-label">Total DEF</div><div class="def-stat-value">#'+m.totalRank+'</div></div>'+ 
    '<div class="def-stat"><div class="def-stat-label">Scoring DEF</div><div class="def-stat-value">#'+m.scoringRank+'</div></div>'+ 
    '<div class="def-stat"><div class="def-stat-label">Sacks</div><div class="def-stat-value">'+m.sacks+'</div></div>'+ 
    '<div class="def-stat"><div class="def-stat-label">INT</div><div class="def-stat-value">'+m.ints+'</div></div>'+ 
    '<div class="def-stat"><div class="def-stat-label">DEF TD</div><div class="def-stat-value">'+m.defTd+'</div></div>'+ 
    '<div class="def-stat"><div class="def-stat-label">Takeaways</div><div class="def-stat-value">'+m.takeaways+'</div></div>'+ 
  '</div>';
}
function defStatsLine(m){
  if(m.fromData)return 'Pts '+m.pointsAllowed+' · Yds '+m.yardsAllowed+' · TO '+m.takeaways+' · Rank #'+m.totalRank;
  return 'Total DEF #'+m.totalRank+' · Sacks '+m.sacks+' · INT '+m.ints+' · Takeaways '+m.takeaways;
}

function pickP(pl,year){
  try{
    var pick=G.DO[G.idx];
    G.roster[pick.sl]={n:pl[1],t:canonicalTeam(pl[3]),e:eraLabel(pl[4]),y:parseInt(year,10),r:pl[5],s:cleanRSStat(pl[6])};
    G.used.add(pl[0]);
    showToast(pl[1]);setTimeout(adv,1100);
  }catch(e){console.warn(e);}
}
function pickU(u){
  try{
    var pick=G.DO[G.idx];
    G.roster[pick.sl]={n:canonicalUnitName(u[0]),t:canonicalTeam(u[1]),e:eraLabel(u[2]),y:u[3],r:u[4],s:cleanRSStat(u[5]),isU:true};
    showToast(u[0]);setTimeout(adv,1100);
  }catch(e){console.warn(e);}
}
function pickD(d,m){
  try{
    G.roster.DEF={n:canonicalUnitName(d[0]),t:canonicalTeam(d[1]),e:eraLabel(d[2]),y:d[3],r:d[4],scheme:d[5],s:cleanRSStat(d[6]),stats:m||defMetricsFromData(d,0),isD:true};
    showToast(d[0]);setTimeout(adv,1100);
  }catch(e){console.warn(e);}
}
function showToast(nm){
  document.getElementById('tnm').textContent=nm;
  var t=document.getElementById('toast');t.classList.add('on');
  setTimeout(function(){t.classList.remove('on');},1500);
}
function adv(){G.idx++;if(G.idx>=G.DO.length){if(G.stage==='offense'){showScr('Ssch');return;}startSeason();return;}refreshDraft();}

function offSlots(){return['QB','RB1','WR1','WR2','WR3','TE','OL'];}
function defSlots(){return ['DEF'];}

function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function cleanRSStat(v){
  return String(v||'')
    .replace(/^\s*[A-Z]{2,5}(?:\/[A-Z]{2,5})?\s+RS\s+(?:only|combined):\s*/i,'')
    .replace(/\bRS\s+combined:\s*/gi,'')
    .replace(/\bcombined:\s*/gi,'')
    .replace(/\bRS\s+records?\b/gi,'records')
    .replace(/\bRS\s+yrs?\b/gi,'seasons')
    .replace(/\bRS\b/gi,'')
    .replace(/\b(MVP|DPOY|OPOY|DROY|OROY)\b/gi,'')
    .replace(/\b(All[- ]Pro(?:\s*1st)?\s*teams?|Pro Bowls?|award(?:s)?)\b/gi,'')
    .replace(/\s+·\s+·\s+/g,' · ')
    .replace(/:\s*·/g,':')
    .replace(/\s+:\s*/g,': ')
    .replace(/\s+([),])/g,'$1')
    .replace(/\(\s+/g,'(')
    .replace(/\s{2,}/g,' ')
    .replace(/(?:·\s*)+$/,'')
    .trim();
}
function fieldName(p){
  if(!p)return 'OPEN';
  if(p.isD)return p.n.replace(' Defense','');
  if(p.isU)return p.n.replace(/ OL$/,'');
  var parts=p.n.split(' ');
  return parts.length>2?parts[0].charAt(0)+'. '+parts.slice(-1)[0]:p.n;
}
function slotMeta(p){
  if(!p)return '';
  if(p.isD&&p.stats)return esc(defStatsLine(p.stats));
  return esc((p.t||'').split(' ').slice(-2).join(' ')+' · '+(p.y||p.e));
}
function clipSlot(sl,x,y,type,cur){
  var p=G.roster[sl], act=sl===cur;
  var cls='clip-slot '+type+(sl==='OL'?' unit-slot':'')+(sl==='DEF'?' def-slot':'')+(p?' filled':' empty')+(act?' act':'');
  var label=sl;
  if(sl==='DEF')label=G.scheme?(G.scheme==='43'?'4-3 DEF':'3-4 DEF'):'DEF';
  return '<div class="'+cls+'" style="left:'+x+'%;top:'+y+'%" title="'+(p?esc(cleanRSStat(p.s)):'Open '+esc(sl))+'">'+
    '<div class="clip-slot-lbl">'+esc(label)+'</div>'+
    '<div class="clip-slot-nm">'+esc(fieldName(p)||'open')+'</div></div>';
}
function clipboardSlotsHtml(cur){
  var a=[];
  a.push(clipSlot('WR1',14,38,'off',cur));
  a.push(clipSlot('WR2',86,38,'off',cur));
  a.push(clipSlot('WR3',28,48,'off',cur));
  a.push(clipSlot('TE',72,52,'off',cur));
  a.push(clipSlot('OL',50,58,'off',cur));
  a.push(clipSlot('QB',50,68,'off',cur));
  a.push(clipSlot('RB1',50,82,'off',cur));
  a.push(clipSlot('DEF',50,18,'def',cur));
  return a.join('');
}

function fieldSlotsHtml(cur){
  var a=[];
  a.push(posNode('WR1',12,69,'off',cur));
  a.push(posNode('WR2',88,69,'off',cur));
  a.push(posNode('WR3',27,64,'off',cur));
  a.push(posNode('TE',68,59,'off',cur));
  a.push(posNode('OL',50,57,'off',cur));
  a.push(posNode('QB',50,72,'off',cur));
  a.push(posNode('RB1',50,82,'off',cur));
  a.push(defUnitNode(cur));
  return a.join('');
}
function posNode(sl,x,y,type,cur){
  var p=G.roster[sl], act=sl===cur;
  var cls='fpos '+type+(sl==='OL'?' unit':'')+(p?' filled':' empty')+(act?' act':'');
  var label=sl;
  return '<div class="'+cls+'" style="left:'+x+'%;top:'+y+'%" title="'+(p?esc(cleanRSStat(p.s)):'Open '+esc(sl))+'">'+
    '<div class="fsl">'+esc(label)+'</div><div class="fnm">'+esc(fieldName(p))+'</div>'+
    '<div class="fmeta">'+slotMeta(p)+'</div>'+(p?'<div class="frtg">'+p.r+'</div>':'')+'</div>';
}
function defUnitNode(cur){
  var p=G.roster.DEF, act=cur==='DEF';
  var cls='fpos def defunit'+(p?' filled':' empty')+(act?' act':'');
  var label=G.scheme?(G.scheme==='43'?'4-3 DEF UNIT':'3-4 DEF UNIT'):'DEF AFTER OFFENSE';
  return '<div class="'+cls+'" style="left:50%;top:30%" title="'+(p?esc(cleanRSStat(p.s)):'Choose defensive scheme after offense')+'">'+
    '<div class="fsl">'+esc(label)+'</div><div class="fnm">'+esc(fieldName(p))+'</div>'+
    '<div class="fmeta">'+(p?esc(defStatsLine(p.stats||{totalRank:'—',scoringRank:'—',sacks:'—',ints:'—',defTd:'—',takeaways:'—'})):'Top 3 by year · #1 = best D')+'</div>'+(p?'<div class="frtg">'+p.r+'</div>':'')+'</div>';
}

function renderClip(){
  var curSlot=G.idx<G.DO.length?G.DO[G.idx].sl:'';
  var t=calcTR();var gct=gc(t);
  document.getElementById('clip-ovr').textContent=t>0?'OVR '+t+' '+gct.g:'OVR —';
  document.getElementById('field-slots').innerHTML=clipboardSlotsHtml(curSlot);
}

function startSeason(){
  showScr('S2');
  var myTR=calcTR();G.tr=myTR;var gct=gc(myTR);
  document.getElementById('sea-sub').textContent=(G.scheme==='43'?'4-3':'3-4')+' DEFENSIVE TEAM UNIT · 17 GAMES · 18 WEEKS · REGULAR-SEASON ONLY · 1999–2025';
  document.getElementById('sc').innerHTML=
    '<div class="stat-rules"><strong>Randomization:</strong> Team/year spins use uniform probability over every valid option. Game outcomes use Elo-style win % from roster rating vs opponent (10%–93% floor/ceiling). Schedule order is shuffled each season. Range: <strong>1999–2025</strong>.</div>'+ 
    '<div class="field-card final-field">'+
      '<div class="clip-top"><span class="clip-ttl">🏈 FINAL FIELD DEPTH CHART · '+(G.scheme==='43'?'4-3':'3-4')+' TEAM DEFENSE</span><span><span class="clip-ovr" style="color:'+gct.c+'">OVR '+myTR+' '+gct.g+'</span></span></div>'+ 
      '<div class="field-note">Offense: QB · 1 RB · 3 WR · TE · statistical OL unit. Defense: one full-team defensive unit by selected year (#1 = best D that year).</div>'+ 
      '<div class="field-wrap"><div class="fzone def">DEFENSE</div><div class="fzone off">OFFENSE</div><div class="fhash"></div><div class="fmid">17-0</div>'+fieldSlotsHtml('')+'</div>'+ 
      '<div class="field-legend"><span>Blue = offense</span><span>Red = defensive team unit</span><span>Gold = OL unit</span></div>'+ 
    '</div>'+ 
    '<div style="text-align:center;padding:18px 18px 32px"><button class="btn bg" id="kickBtn">🏈 KICK OFF — CHASE 17-0</button></div>';
  document.getElementById('kickBtn').addEventListener('click',runSeason);
}

function wp(mine,opp){return winProbability(mine,opp);}
function gsc(won,diff){
  if(won){var my=17+randInt(18);var mg=3+randInt(14)+Math.max(0,Math.floor(diff/3));return[my,Math.max(0,my-mg)];}
  var op=17+randInt(17);var mg=1+randInt(13)+Math.max(0,Math.floor(-diff/3));return[Math.max(0,op-mg),op];
}

function runSeason(){
  try{
    var myR=G.tr;
    var schedule=shuffle(RSG);
    var all=[];var wk=1;
    for(var i=0;i<schedule.length;i++){
      if(i===BYE_AFTER){all.push({bye:true,wk:'WEEK '+wk});wk++;}
      all.push({o:schedule[i].o,r:schedule[i].r,wk:'WEEK '+wk,pl:false});wk++;
    }
    G.games=[];
    for(var i=0;i<all.length;i++){
      if(all[i].bye){G.games.push(all[i]);continue;}
      var won=randFloat()<wp(myR,all[i].r);
      var sc=gsc(won,myR-all[i].r);
      G.games.push({o:all[i].o,r:all[i].r,wk:all[i].wk,pl:all[i].pl,won:won,ms:sc[0],os:sc[1]});
    }
    document.getElementById('sc').innerHTML=
      '<div class="trat" style="padding:9px 14px"><div class="trl">RATING: <strong style="color:var(--g)">'+myR+'</strong> &nbsp;|&nbsp; '+(G.scheme==='43'?'4-3':'3-4')+' &nbsp;|&nbsp; GOAL: <strong style="color:var(--g)">17-0</strong></div>'+
      '<div class="recbar"><div class="rbw" id="rw">0</div><div class="rbd">-</div><div class="rbl" id="rlx">0</div></div></div>'+
      '<div class="gw" id="gl"><div class="gst">REGULAR SEASON RESULTS — 17 GAMES · 18 WEEKS</div></div>';
    var idx=0,wins=0,losses=0,phAdded=false;
    function next(){
      if(idx>=G.games.length){setTimeout(function(){endScreen(wins,losses);},600);return;}
      var g=G.games[idx];idx++;
      var gl=document.getElementById('gl');
      if(g.bye){
        var byeRow=document.createElement('div');
        byeRow.className='gr bye on';
        byeRow.innerHTML='<div class="gwk">'+esc(g.wk)+'</div><div class="gop">BYE WEEK</div><div class="gsc">REST</div>';
        gl.appendChild(byeRow);setTimeout(next,90);return;
      }
      if(g.won)wins++;else losses++;
      var row=document.createElement('div');
      row.className='gr '+(g.won?'wn':'ls');
      row.innerHTML='<div class="gwk">'+esc(g.wk)+'</div><div class="gop">vs '+esc(g.o)+'</div><div class="gsc '+(g.won?'wn':'ls')+'">'+g.ms+'–'+g.os+'</div><div class="grs '+(g.won?'wn':'ls')+'">'+(g.won?'W':'L')+'</div>';
      gl.appendChild(row);
      requestAnimationFrame(function(){row.classList.add('on');});
      document.getElementById('rw').textContent=wins;
      document.getElementById('rlx').textContent=losses;
      setTimeout(next,110);
    }
    next();
  }catch(e){console.error(e);}
}

function rankFromRating(r,offset){
  return Math.max(1,Math.min(32,Math.round(33-((r-80)*1.7)+offset)));
}
function performanceLines(){
  var qb=G.roster.QB||{}, rb=G.roster.RB1||{}, wr=G.roster.WR1||{}, def=G.roster.DEF||{};
  var boost=Math.max(0,G.tr-88);
  return [
    {label:'Passing leader',name:qb.n||'Quarterback',value:(4050+boost*105)+' YDS · '+(28+Math.round(boost*1.2))+' TD'},
    {label:'Rushing leader',name:rb.n||'Running back',value:(1120+boost*42)+' YDS · '+(9+Math.round(boost*.55))+' TD'},
    {label:'Receiving leader',name:wr.n||'Wide receiver',value:(1180+boost*48)+' YDS · '+(8+Math.round(boost*.5))+' TD'},
    {label:'Defense',name:def.n||'Defensive unit',value:(42+boost)+' SACKS · '+(18+Math.round(boost*.7))+' TAKEAWAYS'}
  ];
}
function scheduleHtml(){
  return G.games.filter(function(g){return !g.bye;}).map(function(g){
    return '<div class="ei"><div class="eil"><div class="eip">'+esc(g.wk)+'</div><div class="ein">vs '+esc(g.o)+'</div></div><div class="eir">'+(g.won?'W ':'L ')+g.ms+'–'+g.os+'</div></div>';
  }).join('');
}
function endScreen(wins,losses){
  var perfect=wins===17&&losses===0, offRank=rankFromRating(G.tr,0), defRating=(G.roster.DEF&&G.roster.DEF.r)||G.tr, defRank=rankFromRating(defRating,-1);
  var ptsFor=0,ptsAgainst=0;
  G.games.forEach(function(g){if(!g.bye){ptsFor+=g.ms;ptsAgainst+=g.os;}});
  var perf=performanceLines().map(function(p){
    return '<div class="ei"><div class="eil"><div class="eip">'+esc(p.label)+'</div><div class="ein">'+esc(p.name)+'</div></div><div class="eit">'+esc(p.value)+'</div></div>';
  }).join('');
  var summary=perfect?'Perfect season complete. Your roster went unbeaten against 17 elite opponents.':'The perfect season ended, but your all-time roster finished '+wins+'–'+losses+' against an elite 17-game schedule.';
  showScr('S3');
  document.getElementById('S3').className='scr on '+(perfect?'perf':'def');
  document.getElementById('ec').innerHTML=
    '<div class="tagline">1999–2025 PERFECT SEASON SIMULATOR</div>'+
    '<div class="etl '+(perfect?'pf':'lf')+'">'+(perfect?'PERFECT SEASON':'SEASON COMPLETE')+'</div>'+
    '<div class="erec">FINAL RECORD · '+wins+'–'+losses+'</div>'+
    '<div class="edsc">'+esc(summary)+'</div>'+
    '<div class="egrd"><div class="ei"><div class="eil"><div class="eip">Offensive rank</div><div class="ein">League simulation</div></div><div class="eir">#'+offRank+'</div></div>'+
    '<div class="ei"><div class="eil"><div class="eip">Defensive rank</div><div class="ein">League simulation</div></div><div class="eir">#'+defRank+'</div></div>'+
    '<div class="ei"><div class="eil"><div class="eip">Points scored</div><div class="ein">17 games</div></div><div class="eir">'+ptsFor+'</div></div>'+
    '<div class="ei"><div class="eil"><div class="eip">Points allowed</div><div class="ein">17 games</div></div><div class="eir">'+ptsAgainst+'</div></div></div>'+
    '<div class="gst">TOP PLAYER &amp; TEAM PERFORMANCES</div><div class="egrd">'+perf+'</div>'+
    '<div class="gst">FULL 17-GAME SCHEDULE</div><div class="egrd">'+scheduleHtml()+'</div>'+
    '<button class="btn bg" id="againBtn">BUILD ANOTHER PERFECT SEASON</button>';
  document.getElementById('againBtn').addEventListener('click',startDraft);
  if(perfect)confetti();
}
function confetti(){
  var root=document.getElementById('cfx');root.innerHTML='';
  for(var i=0;i<55;i++){
    var p=document.createElement('div');p.className='cf';p.textContent='■';
    p.style.left=randFloat()*100+'%';p.style.color=['#111827','#6b7280','#d4af37'][i%3];
    p.style.animationDuration=(1.5+randFloat()*2)+'s';p.style.animationDelay=(randFloat()*.6)+'s';root.appendChild(p);
  }
  setTimeout(function(){root.innerHTML='';},4200);
}


function initGameData(data){
  PL=data.players||[];
  OLU=data.ol_units||[];
  DEFU=data.defense_units||[];
  TMS=data.teams||[];
  UNIT_YEARS=data.unit_years||[];
  normalizeFranchiseData();
  buildIndices();
  var loading=document.getElementById('loading');
  if(loading)loading.style.display='none';
  var startBtn=document.getElementById('startBtn');
  if(startBtn)startBtn.disabled=false;
  var badge=document.getElementById('build-badge');
  var build=window.__APP_BUILD__||'unknown';
  if(badge)badge.textContent='Build '+build;
}

loadGameData()
  .then(initGameData)
  .catch(function(err){
    var loading=document.getElementById('loading');
    if(loading){
      setLoading('Failed to load NFL data','Please refresh and try again');
      var sub=document.getElementById('loading-sub');
      if(sub)sub.textContent=err.message;
    }
    console.error(err);
  });

document.getElementById('startBtn').addEventListener('click',startDraft);
document.getElementById('sch43').addEventListener('click',function(){selectScheme('43');});
document.getElementById('sch34').addEventListener('click',function(){selectScheme('34');});
document.getElementById('spbtn').addEventListener('click',doSpin);
document.getElementById('rrteam').addEventListener('click',rerollTeam);
document.getElementById('rrera').addEventListener('click',rerollEra);
