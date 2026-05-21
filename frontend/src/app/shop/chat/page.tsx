'use client';

import RoleGuard from '@/components/auth/RoleGuard';
import ChatPage from '../../chat/page';

export default function ShopperChatPage() {
  return (
    <RoleGuard allowed={['shopper']}>
      <ChatPage />
    </RoleGuard>
  );
}
