"use client";

import { useState, useEffect } from "react";
import { api } from "../../../lib/api";
import { useAuth } from "../../../context/AuthContext";
import { UserPlus, Trash2, Edit2, Shield, User, X, Save, Loader2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { motion } from "framer-motion";

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
      <div className="p-8 min-h-screen flex items-center justify-center bg-[#f8fafc]">
        <p className="text-slate-500 font-medium">Akses ditolak. Hanya admin yang dapat mengakses halaman ini.</p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-5xl mx-auto px-4 sm:px-6 md:px-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 sm:mb-8"
      >
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">User Management</h1>
          <p className="text-slate-500 mt-2 text-xs sm:text-sm">
            Kelola akun pengguna sistem EnterpriseMind AI
          </p>
        </div>
        <Button
          onClick={() => setShowCreateModal(true)}
          className="bg-[#0077ff] hover:bg-[#0047b3] text-white gap-2 font-semibold shadow-sm w-full sm:w-auto"
        >
          <UserPlus className="w-4 h-4" />
          Tambah User
        </Button>
      </motion.div>

      {/* Users - Mobile Cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="md:hidden"
      >
        <div className="space-y-3">
          {isLoading ? (
            <div className="text-center py-12 text-slate-400">
              <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-[#0077ff]" />
              Memuat data pengguna...
            </div>
          ) : users.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              Belum ada pengguna terdaftar.
            </div>
          ) : (
            users.map((u) => (
              <Card key={u.id} className="bg-white border-slate-200 shadow-sm">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-10 h-10 rounded-full bg-[#0077ff]/10 flex items-center justify-center border border-[#0077ff]/20 shrink-0">
                        {u.role === "admin" ? (
                          <Shield className="w-5 h-5 text-[#0077ff]" />
                        ) : (
                          <User className="w-5 h-5 text-slate-500" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <p className="font-semibold text-slate-900 text-sm truncate">{u.full_name}</p>
                        <p className="text-xs text-slate-500 truncate">{u.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setEditingUser({ ...u })}
                        className="h-8 w-8 text-slate-500 hover:text-[#0077ff] hover:bg-[#0077ff]/5 bg-transparent"
                        title="Edit"
                      >
                        <Edit2 className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDeleteUser(u.id, u.email)}
                        className="h-8 w-8 text-slate-500 hover:text-rose-600 hover:bg-rose-50 bg-transparent"
                        title="Hapus"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mt-3">
                    <Badge className={`shadow-none font-medium capitalize text-xs ${
                      u.role === "admin"
                        ? "bg-[#0077ff]/10 text-[#0077ff] border-[#0077ff]/20 border"
                        : "bg-slate-200/60 text-slate-700 border-slate-200 border"
                    }`}>
                      {u.role}
                    </Badge>
                    <Badge className={`shadow-none font-medium capitalize text-xs ${
                      u.is_active
                        ? "bg-emerald-50 text-emerald-800 border-emerald-200 border"
                        : "bg-rose-50 text-rose-800 border-rose-200 border"
                    }`}>
                      {u.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </motion.div>

      {/* Users Table - Desktop */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="hidden md:block"
      >
        <Card className="shadow-sm border-slate-200 overflow-hidden bg-white">
          <div className="overflow-x-auto bg-white">
            <Table className="bg-white">
              <TableHeader className="bg-[#f8fafc]">
                <TableRow className="bg-transparent hover:bg-transparent border-b border-slate-200">
                  <TableHead className="font-semibold text-slate-700 px-4">Nama</TableHead>
                  <TableHead className="font-semibold text-slate-700 px-4">Email</TableHead>
                  <TableHead className="font-semibold text-slate-700 px-4">Role</TableHead>
                  <TableHead className="font-semibold text-slate-700 px-4">Status</TableHead>
                  <TableHead className="font-semibold text-slate-700 hidden lg:table-cell px-4">Dibuat</TableHead>
                  <TableHead className="font-semibold text-slate-700 text-right px-4">Aksi</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="bg-white">
                {isLoading ? (
                  <TableRow className="bg-transparent hover:bg-transparent">
                    <TableCell colSpan={6} className="text-center py-12 text-slate-400 bg-transparent">
                      <Loader2 className="w-5 h-5 animate-spin mx-auto mb-2 text-[#0077ff]" />
                      Memuat data pengguna...
                    </TableCell>
                  </TableRow>
                ) : users.length === 0 ? (
                  <TableRow className="bg-transparent hover:bg-transparent">
                    <TableCell colSpan={6} className="text-center py-12 text-slate-400 bg-transparent">
                      Belum ada pengguna terdaftar.
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((u) => (
                    <TableRow key={u.id} className="bg-transparent hover:bg-[#0077ff]/5 border-b border-slate-200/60 transition-colors">
                      <TableCell className="bg-transparent px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-[#0077ff]/10 flex items-center justify-center border border-[#0077ff]/20 shrink-0">
                            {u.role === "admin" ? (
                              <Shield className="w-4 h-4 text-[#0077ff]" />
                            ) : (
                              <User className="w-4 h-4 text-slate-500" />
                            )}
                          </div>
                          <span className="font-semibold text-slate-900">{u.full_name}</span>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-slate-600 text-sm px-4 py-3 bg-transparent">{u.email}</TableCell>
                      <TableCell className="px-4 py-3 bg-transparent">
                        <Badge className={`shadow-none font-medium capitalize text-xs ${
                          u.role === "admin"
                            ? "bg-[#0077ff]/10 text-[#0077ff] border-[#0077ff]/20 border"
                            : "bg-slate-200/60 text-slate-700 border-slate-200 border"
                        }`}>
                          {u.role}
                        </Badge>
                      </TableCell>
                      <TableCell className="px-4 py-3 bg-transparent">
                        <Badge className={`shadow-none font-medium capitalize text-xs ${
                          u.is_active
                            ? "bg-emerald-50 text-emerald-800 border-emerald-200 border"
                            : "bg-rose-50 text-rose-800 border-rose-200 border"
                        }`}>
                          {u.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-slate-600 text-sm hidden lg:table-cell px-4 py-3 bg-transparent">
                        {new Date(u.created_at).toLocaleDateString("id-ID")}
                      </TableCell>
                      <TableCell className="text-right px-4 py-3 bg-transparent">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setEditingUser({ ...u })}
                            className="h-8 w-8 text-slate-500 hover:text-[#0077ff] hover:bg-[#0077ff]/5 bg-transparent"
                            title="Edit"
                          >
                            <Edit2 className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDeleteUser(u.id, u.email)}
                            className="h-8 w-8 text-slate-500 hover:text-rose-600 hover:bg-rose-50 bg-transparent"
                            title="Hapus"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </Card>
      </motion.div>

      {/* Create User Dialog */}
      <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
        <DialogContent className="sm:max-w-[425px] bg-white">
          <DialogHeader>
            <DialogTitle className="text-slate-900">Tambah User Baru</DialogTitle>
            <DialogDescription className="text-slate-500">
              Buat akun baru untuk memberikan akses ke EnterpriseMind AI.
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-lg p-3 text-sm font-medium">
              {error}
            </div>
          )}

          <form onSubmit={handleCreateUser} className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="name" className="text-slate-700 font-medium">Nama Lengkap</Label>
              <Input
                id="name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                required
                placeholder="Super Admin"
                className="bg-white border-slate-300 focus-visible:ring-[#0077ff] text-slate-800"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-slate-700 font-medium">Email</Label>
              <Input
                id="email"
                type="email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                required
                placeholder="admin@enterprise.com"
                className="bg-white border-slate-300 focus-visible:ring-[#0077ff] text-slate-800"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-slate-700 font-medium">Password</Label>
              <Input
                id="password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={6}
                placeholder="••••••"
                className="bg-white border-slate-300 focus-visible:ring-[#0077ff] text-slate-800"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="role" className="text-slate-700 font-medium">Role</Label>
              <select
                id="role"
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0077ff]/50 shadow-sm text-sm"
              >
                <option value="user">User</option>
                <option value="admin">Admin</option>
                <option value="analyst">Analyst</option>
                <option value="viewer">Viewer</option>
              </select>
            </div>
            <DialogFooter className="pt-4">
              <Button
                type="submit"
                disabled={isSubmitting}
                className="w-full bg-[#0077ff] hover:bg-[#0047b3] text-white gap-2 font-semibold shadow-sm"
              >
                {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
                {isSubmitting ? "Membuat..." : "Buat User"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit User Dialog */}
      <Dialog open={editingUser !== null} onOpenChange={(open) => !open && setEditingUser(null)}>
        {editingUser && (
          <DialogContent className="sm:max-w-[425px] bg-white">
            <DialogHeader>
              <DialogTitle className="text-slate-900">Edit User</DialogTitle>
              <DialogDescription className="text-slate-500">
                Ubah informasi profil atau peran akun ini.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-2">
              <div className="space-y-1.5">
                <Label htmlFor="edit-name" className="text-slate-700 font-medium">Nama Lengkap</Label>
                <Input
                  id="edit-name"
                  value={editingUser.full_name}
                  onChange={(e) => setEditingUser({ ...editingUser, full_name: e.target.value })}
                  className="bg-white border-slate-300 focus-visible:ring-[#0077ff] text-slate-800"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="edit-role" className="text-slate-700 font-medium">Role</Label>
                <select
                  id="edit-role"
                  value={editingUser.role}
                  onChange={(e) => setEditingUser({ ...editingUser, role: e.target.value })}
                  className="w-full bg-white border border-slate-300 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0077ff]/50 shadow-sm text-sm"
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                  <option value="analyst">Analyst</option>
                  <option value="viewer">Viewer</option>
                </select>
              </div>
              <div className="flex items-center gap-3.5 pt-2">
                <input
                  type="checkbox"
                  id="edit-active"
                  checked={editingUser.is_active}
                  onChange={(e) => setEditingUser({ ...editingUser, is_active: e.target.checked })}
                  className="cursor-pointer h-4 w-4 rounded border-slate-300 text-[#0077ff] focus:ring-[#0077ff]"
                />
                <Label htmlFor="edit-active" className="cursor-pointer font-medium text-slate-800">
                  Akun Aktif
                </Label>
              </div>
              <DialogFooter className="pt-4">
                <Button
                  onClick={handleUpdateUser}
                  disabled={isSubmitting}
                  className="w-full bg-[#0077ff] hover:bg-[#0047b3] text-white gap-2 font-semibold shadow-sm"
                >
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  {isSubmitting ? "Menyimpan..." : "Simpan Perubahan"}
                </Button>
              </DialogFooter>
            </div>
          </DialogContent>
        )}
      </Dialog>
    </div>
  );
}
