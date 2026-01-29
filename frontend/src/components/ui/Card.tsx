import { ReactNode } from 'react'
import { motion } from 'framer-motion'
import './Card.css'

interface CardProps {
  children: ReactNode
  className?: string
  hover?: boolean
}

export default function Card({ children, className = '', hover = false }: CardProps) {
  return (
    <motion.div
      className={`card ${className}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      whileHover={hover ? { y: -4, boxShadow: '0 8px 24px rgba(74, 124, 89, 0.12)' } : {}}
    >
      {children}
    </motion.div>
  )
}
