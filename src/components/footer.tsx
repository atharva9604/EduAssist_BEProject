import React from 'react'

const Footer = () => {
  return (
    <footer id="contact" className="px-12 py-10 bg-gray-900 text-gray-400 border-t border-gray-800">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <p>© {new Date().getFullYear()} EduAssist. All rights reserved.</p>
          <div className="flex gap-6 mt-4 md:mt-0">
            <a href="#" className="hover:text-[#DAA520]">Privacy Policy</a>
            <a href="#" className="hover:text-[#DAA520]">Terms</a>
            <a href="mailto:contact@eduassist.com" className="hover:text-[#DAA520]">
              contact@eduassist.com
            </a>
          </div>
        </div>
    </footer>
  )
}

export default Footer
