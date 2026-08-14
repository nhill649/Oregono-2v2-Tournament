export const PLAYERS = [
  { id:'thunderpants324', name:'Thunderpants324', aliases:['Thunderpants324'] },
  { id:'prestochango884', name:'Prestochango884', aliases:['Prestochango884'] },
  { id:'xajopasa', name:'XaJoPaSa', aliases:['XaJoPaSa'] },
  { id:'nitro-lox', name:'Nitro lox', aliases:['Nitro lox','Nitro lox4261'] },
  { id:'muffinman', name:'Muffinman', aliases:['Muffinman','Muffinman1253'] },
  { id:'restoredcamp884', name:'Restoredcamp884', aliases:['Restoredcamp884','Soggybread12344'] },
  { id:'patenthorse2227', name:'PatentHorse2227', aliases:['PatentHorse2227'] },
  { id:'ez-vxvid', name:'EZ Vxvid', aliases:['EZ Vxvid','Guest-foJ1Rqnx'] }
];

export const PLAYER_BY_NAME = new Map(
  PLAYERS.flatMap(player => player.aliases.map(alias => [alias.toLowerCase(), player]))
);
