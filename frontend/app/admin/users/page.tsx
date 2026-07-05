"use client";

import { useState, useEffect } from "react";
import { api } from "../../../lib/api";
import { useAuth } from "../../../context/AuthContext";
import { UserPlus, Trash2, Edit2, Shield, User, X, Save, Loader2 } from "lucide-react";

interface UserData {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export default function UsersPage() {
  const { isAdmin } = useAuth();
  const [users, setUsers] = useState<UserData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingUser, setEditingUser] = useState<UserData | null>(null);

  // Create form state
  const [newEmail, setNewEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("user");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    setIsLoading(true);
    try {
      const data = await api.getUsers();
      setUsers(data);
    } catch (err) {
      console.error("Failed to load users:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      await api.createUser({
        email: newEmail,
        password: newPassword,
        full_name: newName,
        role: newRole,
      });
      setShowCreateModal(false);
      setNewEmail("");
      setNewPassword("");
      setNewName("");
      setNewRole("user");
      loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal membuat user.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateUser = async () => {
    if (!editingUser) return;
    setIsSubmitting(true);
    try {
      await api.updateUser(editingUser.id, {
        full_name: editingUser.full_name,
        role: editingUser.role,
        is_active: editingUser.is_active,
      });
      setEditingUser(null);
      loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Gagal update user.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteUser = async (userId: string, email: string) => {
    if (!confirm(`Hapus user ${email}?`)) return;
    try {
      await api.deleteUser(userId);
      loadUsers();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Gagal hapus user.");
    }
  };

  if (!isAdmin) {
    return (
      <div className="p-margin min-h-screen flex items-center justify-center">
        <p className="text-on-surface-variant">Akses ditolak. Hanya admin yang dapat mengakses halaman ini.</p>
      </div>
    );
  }

  return (
    <div className="p-margin min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-h2 text-h2 text-on-surface font-semibold">User Management</h1>
          <p className="font-body-sm text-body-sm text-on-surface-variant mt-1">
            Kelola akun pengguna sistem EnterpriseMind AI
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-brass text-on-primary font-body-sm text-body-sm font-semibold px-5 py-2.5 rounded hover:brightness-110 transition-all flex items-center gap-2 cursor-pointer"
        >
          <UserPlus className="w-4 h-4" />
          Tambah User
        </button>
      </div>

      {/* Users Table */}
      <div className="bg-surface-container border border-outline-variant rounded-lg overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-outline-variant bg-surface-container-high">
              <th className="text-left px-6 py-3 font-data-label text-data-label text-on-surface-variant uppercase tracking-widest">Nama</th>
              <th className="text-left px-6 py-3 font-data-label text-data-label text-on-surface-variant uppercase tracking-widest">Email</th>
              <th className="text-left px-6 py-3 font-data-label text-data-label text-on-surface-variant uppercase tracking-widest">Role</th>
              <th className="text-left px-6 py-3 font-data-label text-data-label text-on-surface-variant uppercase tracking-widest">Status</th>
              <th className="text-left px-6 py-3 font-data-label text-data-label text-on-surface-variant uppercase tracking-widest">Dibuat</th>
              <th className="text-right px-6 py-3 font-data-label text-data-label text-on-surface-variant uppercase tracking-widest">Aksi</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={6} className="text-center py-12 text-on-surface-variant">
                  <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2" />
                  Memuat data...
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-12 text-on-surface-variant">
                  Belum ada user.
                </td>
              </tr>
            ) : (
              users.map((u) => (
                <tr key={u.id} className="border-b border-outline-variant/50 hover:bg-surface-container-high transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-surface-container-highest flex items-center justify-center border border-outline-variant">
                        {u.role === "admin" ? (
                          <Shield className="w-4 h-4 text-brass" />
                        ) : (
                          <User className="w-4 h-4 text-on-surface-variant" />
                        )}
                      </div>
                      <span className="font-body-sm text-body-sm text-on-surface">{u.full_name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 font-data-mono text-data-mono text-on-surface-variant">{u.email}</td>
                  <td className="px-6 py-4">
                    <span className={`font-data-label text-[10px] uppercase px-2 py-1 rounded ${
                      u.role === "admin"
                        ? "bg-brass/20 text-brass"
                        : "bg-secondary/20 text-secondary"
                    }`}>
                      {u.role}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`font-data-label text-[10px] uppercase px-2 py-1 rounded ${
                      u.is_active
                        ? "bg-cyan/20 text-cyan"
                        : "bg-error/20 text-error"
                    }`}>
                      {u.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-6 py-4 font-data-mono text-data-mono text-on-surface-variant">
                    {new Date(u.created_at).toLocaleDateString("id-ID")}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => setEditingUser({ ...u })}
                        className="p-2 hover:bg-surface-container-highest rounded transition-colors text-on-surface-variant hover:text-secondary cursor-pointer"
                        title="Edit"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteUser(u.id, u.email)}
                        className="p-2 hover:bg-surface-container-highest rounded transition-colors text-on-surface-variant hover:text-error cursor-pointer"
                        title="Hapus"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create User Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-surface-container border border-outline-variant rounded-lg p-8 w-full max-w-md shadow-xl">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-h3 text-h3 text-on-surface">Tambah User Baru</h2>
              <button onClick={() => setShowCreateModal(false)} className="text-on-surface-variant hover:text-on-surface cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            {error && (
              <div className="bg-error/10 border border-error/30 text-error rounded px-4 py-3 mb-4 font-body-sm text-body-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleCreateUser} className="space-y-4">
              <div>
                <label className="block font-data-label text-data-label text-on-surface-variant uppercase tracking-widest mb-1">Nama Lengkap</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  required
                  className="w-full bg-surface-container-high border border-outline rounded py-2.5 px-4 text-on-surface font-body-sm text-body-sm focus:border-secondary focus:ring-1 focus:ring-secondary transition-all"
                />
              </div>
              <div>
                <label className="block font-data-label text-data-label text-on-surface-variant uppercase tracking-widest mb-1">Email</label>
                <input
                  type="email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  required
                  className="w-full bg-surface-container-high border border-outline rounded py-2.5 px-4 text-on-surface font-body-sm text-body-sm focus:border-secondary focus:ring-1 focus:ring-secondary transition-all"
                />
              </div>
              <div>
                <label className="block font-data-label text-data-label text-on-surface-variant uppercase tracking-widest mb-1">Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={6}
                  className="w-full bg-surface-container-high border border-outline rounded py-2.5 px-4 text-on-surface font-body-sm text-body-sm focus:border-secondary focus:ring-1 focus:ring-secondary transition-all"
                />
              </div>
              <div>
                <label className="block font-data-label text-data-label text-on-surface-variant uppercase tracking-widest mb-1">Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full bg-surface-container-high border border-outline rounded py-2.5 px-4 text-on-surface font-body-sm text-body-sm focus:border-secondary focus:ring-1 focus:ring-secondary transition-all cursor-pointer"
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-brass text-on-primary font-body-sm text-body-sm font-semibold py-3 rounded hover:brightness-110 transition-all flex justify-center items-center gap-2 disabled:opacity-50 cursor-pointer"
              >
                {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
                {isSubmitting ? "Membuat..." : "Buat User"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Edit User Modal */}
      {editingUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-surface-container border border-outline-variant rounded-lg p-8 w-full max-w-md shadow-xl">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-h3 text-h3 text-on-surface">Edit User</h2>
              <button onClick={() => setEditingUser(null)} className="text-on-surface-variant hover:text-on-surface cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block font-data-label text-data-label text-on-surface-variant uppercase tracking-widest mb-1">Nama Lengkap</label>
                <input
                  type="text"
                  value={editingUser.full_name}
                  onChange={(e) => setEditingUser({ ...editingUser, full_name: e.target.value })}
                  className="w-full bg-surface-container-high border border-outline rounded py-2.5 px-4 text-on-surface font-body-sm text-body-sm focus:border-secondary focus:ring-1 focus:ring-secondary transition-all"
                />
              </div>
              <div>
                <label className="block font-data-label text-data-label text-on-surface-variant uppercase tracking-widest mb-1">Role</label>
                <select
                  value={editingUser.role}
                  onChange={(e) => setEditingUser({ ...editingUser, role: e.target.value })}
                  className="w-full bg-surface-container-high border border-outline rounded py-2.5 px-4 text-on-surface font-body-sm text-body-sm focus:border-secondary focus:ring-1 focus:ring-secondary transition-all cursor-pointer"
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="edit-active"
                  checked={editingUser.is_active}
                  onChange={(e) => setEditingUser({ ...editingUser, is_active: e.target.checked })}
                  className="cursor-pointer"
                />
                <label htmlFor="edit-active" className="font-body-sm text-body-sm text-on-surface cursor-pointer">
                  Akun Aktif
                </label>
              </div>
              <button
                onClick={handleUpdateUser}
                disabled={isSubmitting}
                className="w-full bg-brass text-on-primary font-body-sm text-body-sm font-semibold py-3 rounded hover:brightness-110 transition-all flex justify-center items-center gap-2 disabled:opacity-50 cursor-pointer"
              >
                {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                {isSubmitting ? "Menyimpan..." : "Simpan Perubahan"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
