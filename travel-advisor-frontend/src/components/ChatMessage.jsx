import { Compass, UserRound } from 'lucide-react';
import Markdown from 'react-markdown';
import TripItinerary, { BudgetBreakdown } from './TripItinerary.jsx';
export default function ChatMessage({ message }) {
  const user = message.role === 'user';
  return <article className={`message ${user ? 'user' : 'assistant'}`}><span className="avatar">{user ? <UserRound size={18}/> : <Compass size={20}/>}</span><div className="message-content"><span className="speaker">{user ? 'You' : 'Your travel advisor'}</span><div className="bubble">{user ? <p>{message.content}</p> : message.trip ? <TripItinerary trip={message.trip} budgetDetails={message.budgetDetails}/> : <><Markdown skipHtml>{message.content}</Markdown>{message.budgetDetails && <BudgetBreakdown details={message.budgetDetails}/>}</>}</div></div></article>;
}
