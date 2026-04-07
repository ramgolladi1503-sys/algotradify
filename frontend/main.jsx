
import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";

function App(){
  const [events,setEvents]=useState([]);

  function connect(){
    const ws=new WebSocket("ws://localhost:8000/ws");

    ws.onmessage=e=>{
      const d=JSON.parse(e.data);
      setEvents(prev=>[d,...prev.slice(0,50)]);
    };

    ws.onclose=()=>setTimeout(connect,1000);
  }

  useEffect(()=>{ connect(); },[]);

  return (
    <div style={{background:"black",color:"white",padding:20}}>
      <h2>Live Feed</h2>

      {events.map((e,i)=>(
        <div key={i} style={{border:"1px solid #333",padding:10,marginBottom:10}}>
          <div>{e.type}</div>
          <div>{JSON.stringify(e.payload)}</div>
        </div>
      ))}
    </div>
  );
}

createRoot(document.getElementById("root")).render(<App/>);
