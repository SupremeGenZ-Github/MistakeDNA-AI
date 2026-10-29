export type Skill={id:string;name:string;subject:string;prerequisites:string[];description:string};
export type Question={id:string;subject:string;grade:number;chapter:string;skill:string;difficulty:number;type:'mcq'|'numerical';prompt:string;options?:string[];answer:string;tolerance?:number;explanation:string;hint:string;misconceptions:Record<string,string>};
