import { Compass, Plus } from 'lucide-react';
export default function Header({ onNewTrip }) {
  return <header className="header"><a className="brand" href="/" aria-label="AI Travel Advisor home"><span className="brand-icon"><Compass size={25}/></span><span>AI Travel Advisor<small>Plan your perfect trip with AI</small></span></a><button className="new-trip" onClick={onNewTrip}><Plus size={17}/> New Trip</button></header>;
}
