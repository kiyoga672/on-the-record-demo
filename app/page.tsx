import {members,coverage} from '@/lib/elastic';
import Home from '@/components/Home';
export const dynamic='force-dynamic';
export default async function Page(){
 try{const [people,cov]=await Promise.all([members(),coverage()]);return <Home people={people} coverage={cov}/>;}
 catch{return <Home people={[]} error="The records service is unavailable. Please retry shortly."/>;}
}
