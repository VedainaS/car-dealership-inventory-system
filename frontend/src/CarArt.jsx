const palettes = [
  { bg: '#d8dcd7', hill: '#c2cdc5', car: '#415f67', light: '#b4c7c8' },
  { bg: '#d8d4cd', hill: '#c6bcae', car: '#6b7166', light: '#bdc1b5' },
  { bg: '#cfd9db', hill: '#bccbd0', car: '#283e49', light: '#adbbc1' },
  { bg: '#d9d6d1', hill: '#c9c5ba', car: '#785b50', light: '#ceb9aa' },
]

export default function CarArt({ vehicle, hero = false }) {
  const p = palettes[(vehicle?.id ?? 0) % palettes.length]
  return (
    <svg className="w-full h-full" viewBox="0 0 640 360" role="img" aria-label={`${vehicle?.make || 'Featured'} car illustration`} preserveAspectRatio="xMidYMid slice">
      <rect width="640" height="360" fill={hero ? '#26403e' : p.bg} />
      <circle cx="520" cy="64" r="100" fill={hero ? '#385652' : '#ffffff'} opacity=".22" />
      <path d="M0 222 Q180 160 342 203 T640 170 V360 H0Z" fill={hero ? '#2e4b48' : p.hill} opacity=".72" />
      <path d="M0 290 Q290 258 640 286 V360 H0Z" fill={hero ? '#1d3433' : '#b8beb8'} opacity=".5" />
      <path d="M0 305 H640" stroke={hero ? '#d9e2d7' : '#f2f1e9'} strokeWidth="2" opacity=".35" strokeDasharray="22 32" />
      <ellipse cx="325" cy="293" rx="239" ry="21" fill="#18272b" opacity=".18" />
      <path d="M95 225 C106 211 144 206 178 201 L236 146 C252 130 276 124 301 124 H412 C435 124 449 133 466 153 L503 195 C536 201 557 212 565 232 L560 266 C555 275 545 280 528 280 H122 C105 280 94 274 90 263Z" fill={hero ? '#b8c3b7' : p.car} />
      <path d="M218 199 L253 155 C262 145 274 141 296 141 H405 C420 141 433 146 445 160 L472 196Z" fill={hero ? '#536d68' : p.light} />
      <path d="M234 195 L259 159 C265 150 274 147 295 147 H331 V195Z M344 147 H403 C419 147 428 153 439 165 L462 195 H344Z" fill={hero ? '#203b3c' : '#506c72'} opacity=".8" />
      <path d="M337 142 V205 M123 215 Q145 208 180 205 M481 203 Q524 209 547 222" stroke={hero ? '#e4ece4' : '#e8e8dd'} opacity=".45" strokeWidth="2" fill="none" />
      <path d="M93 236 H558" stroke="#f9f7f0" strokeWidth="3" opacity=".25" />
      <path d="M98 229 L126 227 L133 240 H94Z" fill="#f4e6ca" />
      <path d="M538 222 L561 233 L561 245 H535Z" fill="#bd614b" />
      <circle cx="183" cy="274" r="38" fill="#1a292d" /><circle cx="183" cy="274" r="24" fill="#c5cbc4" /><circle cx="183" cy="274" r="15" fill="#71817f" />
      <circle cx="474" cy="274" r="38" fill="#1a292d" /><circle cx="474" cy="274" r="24" fill="#c5cbc4" /><circle cx="474" cy="274" r="15" fill="#71817f" />
      <path d="M251 205 H278 M365 205 H391" stroke="#ecf0e9" strokeWidth="3" strokeLinecap="round" opacity=".6" />
    </svg>
  )
}
