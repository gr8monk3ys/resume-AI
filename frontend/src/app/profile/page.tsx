'use client';

import { User, Save } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState, useCallback } from 'react';

import { profileApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';

import type { Profile } from '@/types';


export default function ProfilePage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login');
    }
  }, [user, authLoading, router]);

  const loadProfile = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const data = await profileApi.get();
      setProfile(data);
    } catch (error) {
      console.error('Failed to load profile:', error);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated) {
      void loadProfile()
    }
  }, [isAuthenticated, loadProfile])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthenticated || !profile) return;
    setIsSaving(true);
    setMessage('');
    try {
      const updated = await profileApi.update({
        name: profile.name,
        email: profile.email || undefined,
        phone: profile.phone || undefined,
        linkedin: profile.linkedin || undefined,
        github: profile.github || undefined,
        portfolio: profile.portfolio || undefined,
      });
      setProfile(updated);
      setMessage('Profile saved successfully!');
    } catch (error) {
      console.error('Failed to save profile:', error);
      setMessage('Failed to save profile. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  if (authLoading || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Failed to load profile</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Profile</h1>
        <p className="text-gray-500">Manage your personal information</p>
      </div>

      <form onSubmit={(e) => void handleSave(e)} className="bg-white rounded-lg shadow p-6 space-y-6">
        {message && (
          <div className={`p-3 rounded-md text-sm ${
            message.includes('success') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
          }`}>
            {message}
          </div>
        )}

        <div className="flex items-center space-x-4">
          <div className="bg-primary-100 rounded-full p-4">
            <User className="w-8 h-8 text-primary-600" />
          </div>
          <div>
            <p className="font-medium text-gray-900">{user?.username}</p>
            <p className="text-sm text-gray-500">{user?.email}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="profile-name" className="block text-sm font-medium text-gray-700">Full Name</label>
            <input
              id="profile-name"
              type="text"
              value={profile.name}
              onChange={(e) => setProfile({ ...profile, name: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div>
            <label htmlFor="profile-email" className="block text-sm font-medium text-gray-700">Email</label>
            <input
              id="profile-email"
              type="email"
              value={profile.email || ''}
              onChange={(e) => setProfile({ ...profile, email: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div>
            <label htmlFor="profile-phone" className="block text-sm font-medium text-gray-700">Phone</label>
            <input
              id="profile-phone"
              type="tel"
              value={profile.phone || ''}
              onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <div>
            <label htmlFor="profile-linkedin" className="block text-sm font-medium text-gray-700">LinkedIn</label>
            <input
              id="profile-linkedin"
              type="url"
              value={profile.linkedin || ''}
              onChange={(e) => setProfile({ ...profile, linkedin: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="https://linkedin.com/in/..."
            />
          </div>

          <div>
            <label htmlFor="profile-github" className="block text-sm font-medium text-gray-700">GitHub</label>
            <input
              id="profile-github"
              type="url"
              value={profile.github || ''}
              onChange={(e) => setProfile({ ...profile, github: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="https://github.com/..."
            />
          </div>

          <div>
            <label htmlFor="profile-portfolio" className="block text-sm font-medium text-gray-700">Portfolio</label>
            <input
              id="profile-portfolio"
              type="url"
              value={profile.portfolio || ''}
              onChange={(e) => setProfile({ ...profile, portfolio: e.target.value })}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="https://..."
            />
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isSaving}
            className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50"
          >
            <Save className="w-4 h-4 mr-2" />
            {isSaving ? 'Saving...' : 'Save Profile'}
          </button>
        </div>
      </form>
    </div>
  );
}
