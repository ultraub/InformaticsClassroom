import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  DocumentDuplicateIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline';
import { Card, Button, Badge, Modal, Input } from '../components/common';
import { permissionsService } from '../services/permissions';
import { Permission, type RoleTemplate } from '../types';
import { useUIStore } from '../store/uiStore';

export function RoleTemplates() {
  const queryClient = useQueryClient();
  const { addToast } = useUIStore();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<RoleTemplate | null>(null);

  // Fetch templates
  const { data: templates, isLoading } = useQuery({
    queryKey: ['roleTemplates'],
    queryFn: async () => {
      const response = await permissionsService.getRoleTemplates();
      return response.data || [];
    },
  });

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    permissions: [] as Permission[],
  });

  // Permission categories
  const permissionCategories = {
    'Quiz Management': [
      Permission.QUIZ_VIEW,
      Permission.QUIZ_CREATE,
      Permission.QUIZ_MODIFY,
      Permission.QUIZ_DELETE,
    ],
    'User Management': [
      Permission.USER_VIEW,
      Permission.USER_MANAGE,
    ],
    'Class & System Administration': [
      Permission.TOKEN_GENERATE,
      Permission.CLASS_ADMIN,
      Permission.CLASS_VIEW_ANALYTICS,
      Permission.SYSTEM_ADMIN,
      Permission.SYSTEM_VIEW_LOGS,
    ],
  };

  const createTemplateMutation = useMutation({
    mutationFn: async (template: typeof formData) => {
      const response = await permissionsService.createRoleTemplate({
        ...template,
        isSystem: false,
        createdBy: 'current-user', // TODO: Get from auth
      });
      if (!response.success) {
        throw new Error(response.error || 'Failed to create template');
      }
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roleTemplates'] });
      addToast('Template created successfully', 'success');
      setIsModalOpen(false);
      resetForm();
    },
    onError: (error: Error) => {
      addToast(error.message, 'error');
    },
  });

  const deleteTemplateMutation = useMutation({
    mutationFn: async (templateId: string) => {
      const response = await permissionsService.deleteRoleTemplate(templateId);
      if (!response.success) {
        throw new Error(response.error || 'Failed to delete template');
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roleTemplates'] });
      addToast('Template deleted successfully', 'success');
    },
    onError: (error: Error) => {
      addToast(error.message, 'error');
    },
  });

  const resetForm = () => {
    setFormData({ name: '', description: '', permissions: [] });
    setEditingTemplate(null);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createTemplateMutation.mutate(formData);
  };

  const togglePermission = (permission: Permission) => {
    setFormData((prev) => ({
      ...prev,
      permissions: prev.permissions.includes(permission)
        ? prev.permissions.filter((p) => p !== permission)
        : [...prev.permissions, permission],
    }));
  };

  const handleDuplicate = (template: RoleTemplate) => {
    setFormData({
      name: `${template.name} (Copy)`,
      description: template.description,
      permissions: [...template.permissions],
    });
    setIsModalOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Role Templates</h1>
          <p className="mt-1 text-sm text-gray-500">
            Pre-configured permission sets for quick role assignment
          </p>
        </div>
        <div className="mt-4 sm:mt-0">
          <Button
            variant="primary"
            icon={<PlusIcon className="h-5 w-5" />}
            onClick={() => {
              resetForm();
              setIsModalOpen(true);
            }}
          >
            Create Template
          </Button>
        </div>
      </div>

      {/* Templates Grid */}
      {isLoading ? (
        <div className="p-12 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading templates...</p>
        </div>
      ) : !templates || templates.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <UserGroupIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">
              No templates
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Get started by creating a new role template
            </p>
            <div className="mt-6">
              <Button
                variant="primary"
                icon={<PlusIcon className="h-5 w-5" />}
                onClick={() => setIsModalOpen(true)}
              >
                Create Template
              </Button>
            </div>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {templates.map((template) => (
            <Card key={template.id} padding="md" hover>
              <div className="space-y-4">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 className="text-lg font-medium text-gray-900">
                      {template.name}
                    </h3>
                    {template.isSystem && (
                      <Badge variant="primary" size="sm" className="mt-1">
                        System
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center space-x-1">
                    <button
                      onClick={() => handleDuplicate(template)}
                      className="p-1 text-gray-400 hover:text-gray-600"
                      title="Duplicate"
                    >
                      <DocumentDuplicateIcon className="h-5 w-5" />
                    </button>
                    {!template.isSystem && (
                      <>
                        <button
                          onClick={() => {
                            setEditingTemplate(template);
                            setFormData({
                              name: template.name,
                              description: template.description,
                              permissions: template.permissions,
                            });
                            setIsModalOpen(true);
                          }}
                          className="p-1 text-gray-400 hover:text-primary-600"
                          title="Edit"
                        >
                          <PencilIcon className="h-5 w-5" />
                        </button>
                        <button
                          onClick={() => {
                            if (
                              confirm(
                                `Are you sure you want to delete "${template.name}"?`
                              )
                            ) {
                              deleteTemplateMutation.mutate(template.id);
                            }
                          }}
                          className="p-1 text-gray-400 hover:text-red-600"
                          title="Delete"
                        >
                          <TrashIcon className="h-5 w-5" />
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* Description */}
                <p className="text-sm text-gray-500">{template.description}</p>

                {/* Permissions */}
                <div>
                  <p className="text-xs font-medium text-gray-700 mb-2">
                    Permissions ({template.permissions.length})
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {template.permissions.slice(0, 6).map((permission) => (
                      <Badge key={permission} variant="secondary" size="sm">
                        {permission.split('.')[1]}
                      </Badge>
                    ))}
                    {template.permissions.length > 6 && (
                      <Badge variant="secondary" size="sm">
                        +{template.permissions.length - 6} more
                      </Badge>
                    )}
                  </div>
                </div>

                {/* Apply Button */}
                <Button
                  variant="outline"
                  size="sm"
                  fullWidth
                  onClick={() => {
                    // TODO: Implement apply to user
                    addToast(
                      'Select users to apply this template',
                      'info'
                    );
                  }}
                >
                  Apply to Users
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          resetForm();
        }}
        title={editingTemplate ? 'Edit Template' : 'Create Template'}
        size="lg"
        footer={
          <div className="flex justify-end space-x-3">
            <Button
              variant="outline"
              onClick={() => {
                setIsModalOpen(false);
                resetForm();
              }}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleSubmit}
              loading={createTemplateMutation.isPending}
            >
              {editingTemplate ? 'Update' : 'Create'} Template
            </Button>
          </div>
        }
      >
        <form onSubmit={handleSubmit} className="space-y-6">
          <Input
            label="Template Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            placeholder="e.g., Basic Instructor"
            required
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              placeholder="Brief description of this role template"
              rows={3}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              Permissions
            </label>
            <div className="space-y-4 max-h-96 overflow-y-auto border border-gray-200 rounded-md p-4">
              {Object.entries(permissionCategories).map(
                ([category, permissions]) => (
                  <div key={category}>
                    <h5 className="text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
                      {category}
                    </h5>
                    <div className="space-y-2">
                      {permissions.map((permission) => (
                        <label
                          key={permission}
                          className="flex items-center space-x-2 cursor-pointer hover:bg-gray-50 p-2 rounded"
                        >
                          <input
                            type="checkbox"
                            checked={formData.permissions.includes(permission)}
                            onChange={() => togglePermission(permission)}
                            className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                          />
                          <span className="text-sm text-gray-700">
                            {permission.replace('.', ' - ')}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                )
              )}
            </div>
          </div>

          {formData.permissions.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">
                Selected: {formData.permissions.length} permissions
              </p>
              <div className="flex flex-wrap gap-1">
                {formData.permissions.map((permission) => (
                  <Badge
                    key={permission}
                    variant="primary"
                    size="sm"
                    removable
                    onRemove={() => togglePermission(permission)}
                  >
                    {permission}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </form>
      </Modal>
    </div>
  );
}
